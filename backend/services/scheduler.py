from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import uuid

logger = logging.getLogger(__name__)

class ReminderScheduler:
    def __init__(
        self,
        reminders_collection,
        subscriptions_collection,
        notifications_collection,
        push_service_factory,
        couples_collection=None,
        users_collection=None,
        photos_collection=None,
        settings_collection=None,
    ):
        self.reminders = reminders_collection
        self.subscriptions = subscriptions_collection
        self.notifications = notifications_collection
        self.push_service_factory = push_service_factory
        self.couples = couples_collection
        self.users = users_collection
        self.photos = photos_collection
        self.settings = settings_collection
        self.scheduler = BackgroundScheduler()
        # Track which users have been reminded today/this hour to avoid spam
        self.daily_reminded = {}  # userId -> date string
        self.inactivity_reminded = {}  # userId -> last reminder timestamp
        self.streak_risk_alerted = {}  # coupleId -> date string

    def start(self):
        # Process custom reminders every minute
        self.scheduler.add_job(self.process_due_reminders, IntervalTrigger(seconds=60))
        # Check daily, inactivity, and streak-risk reminders every 5 minutes
        self.scheduler.add_job(self.check_recurring_reminders, IntervalTrigger(seconds=300))
        self.scheduler.start()
        logger.info("Reminder scheduler started")

    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("Reminder scheduler stopped")

    def process_due_reminders(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_process_reminders())
        finally:
            loop.close()

    def check_recurring_reminders(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_check_recurring())
        finally:
            loop.close()

    async def _async_process_reminders(self):
        now = datetime.now(timezone.utc)
        cursor = self.reminders.find(
            {"processed": False, "scheduledAt": {"$lte": now}}
        )
        reminders = await cursor.to_list(length=100)
        push_service = self.push_service_factory()

        for rem in reminders:
            try:
                user_id = rem["userId"]
                message = rem["message"]
                notification_id = str(uuid.uuid4())
                notif_doc = {
                    "id": notification_id,
                    "userId": user_id,
                    "type": "reminder",
                    "title": "Reminder",
                    "message": message,
                    "payload": {"reminderId": str(rem.get("id", rem["_id"]))},
                    "isRead": False,
                    "createdAt": now.isoformat(),
                    "readAt": None,
                }
                await self.notifications.insert_one(notif_doc)
                await push_service.send_notification_to_user(
                    user_id,
                    {
                        "title": "Reminder",
                        "body": message,
                        "url": "/notifications",
                        "notificationId": notification_id,
                        "type": "reminder",
                    },
                )
                await self.reminders.update_one(
                    {"_id": rem["_id"]},
                    {"$set": {"processed": True, "processedAt": now.isoformat()}},
                )
                logger.info(f"Processed reminder {rem['_id']}")
            except Exception as e:
                logger.error(f"Error processing reminder {rem.get('_id')}: {e}")

    async def _async_check_recurring(self):
        """Check all users' settings for daily/inactivity reminders + streak-at-risk alerts."""
        if self.settings is None or self.users is None:
            return
        
        now = datetime.now(timezone.utc)
        push_service = self.push_service_factory()
        
        cursor = self.settings.find({})
        all_settings = await cursor.to_list(length=10000)
        
        for setting in all_settings:
            user_id = setting.get("userId")
            if not user_id:
                continue
            
            # Daily reminder check
            if setting.get("dailyReminderEnabled"):
                await self._handle_daily_reminder(user_id, setting, now, push_service)
            
            # Inactivity reminder check
            if setting.get("inactivityReminderEnabled"):
                await self._handle_inactivity_reminder(user_id, setting, now, push_service)
        
        # Streak-at-risk check for all couples (independent of user settings)
        await self._check_streak_at_risk(now, push_service)

    async def _check_streak_at_risk(self, now, push_service):
        """If past 6pm UTC and a couple has a streak but today's missing a partner upload, alert."""
        if self.couples is None or self.photos is None:
            return
        
        # Only run during specific hours (6pm-10pm UTC)
        if now.hour < 18 or now.hour > 22:
            return
        
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        cursor = self.couples.find({"user2Id": {"$ne": None}})
        all_couples = await cursor.to_list(length=10000)
        
        for couple in all_couples:
            try:
                couple_id = couple["id"]
                # Don't re-alert same day
                if self.streak_risk_alerted.get(couple_id) == today_str:
                    continue
                
                u1 = couple.get("user1Id")
                u2 = couple.get("user2Id")
                if not u1 or not u2:
                    continue
                
                # Get all photos for couple
                cursor = self.photos.find({"coupleId": couple_id}, {"_id": 0})
                photos = await cursor.to_list(length=2000)
                
                from collections import defaultdict
                days = defaultdict(set)
                for p in photos:
                    date_str = p["createdAt"][:10]
                    days[date_str].add(p["uploaderId"])
                
                # Streak only at risk if yesterday both partners sent
                yesterday_uploaders = days.get(yesterday_str, set())
                if u1 not in yesterday_uploaders or u2 not in yesterday_uploaders:
                    continue
                
                today_uploaders = days.get(today_str, set())
                missing_users = [u for u in (u1, u2) if u not in today_uploaders]
                
                if not missing_users:
                    continue  # Both sent today, streak safe
                
                # Send alert to user(s) who haven't sent yet
                for missing_user in missing_users:
                    notif_id = str(uuid.uuid4())
                    await self.notifications.insert_one({
                        "id": notif_id,
                        "userId": missing_user,
                        "type": "streak_at_risk",
                        "title": "🔥 Your streak is in danger!",
                        "message": "Send a photo to your partner today to keep your streak alive!",
                        "payload": {},
                        "isRead": False,
                        "createdAt": now.isoformat(),
                        "readAt": None,
                    })
                    await push_service.send_notification_to_user(
                        missing_user,
                        {
                            "title": "🔥 Streak in danger!",
                            "body": "Send a photo to keep your streak alive!",
                            "url": "/",
                            "notificationId": notif_id,
                            "type": "streak_at_risk",
                        }
                    )
                
                self.streak_risk_alerted[couple_id] = today_str
                logger.info(f"Sent streak-at-risk alert for couple {couple_id}")
            except Exception as e:
                logger.error(f"Streak-at-risk check error for couple {couple.get('id')}: {e}")

    async def _handle_daily_reminder(self, user_id, setting, now, push_service):
        try:
            time_str = setting.get("dailyReminderTime", "20:00")
            hour, minute = map(int, time_str.split(":"))
            
            # Check if current time matches reminder window (within 5-minute window)
            scheduled_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            diff_minutes = abs((now - scheduled_today).total_seconds() / 60)
            
            if diff_minutes > 5:
                return  # Not within window
            
            today_str = now.strftime("%Y-%m-%d")
            if self.daily_reminded.get(user_id) == today_str:
                return  # Already sent today
            
            # Send reminder
            notification_id = str(uuid.uuid4())
            await self.notifications.insert_one({
                "id": notification_id,
                "userId": user_id,
                "type": "daily_reminder",
                "title": "Daily Photo Reminder ✨",
                "message": "Don't forget to share a moment with your partner today!",
                "payload": {},
                "isRead": False,
                "createdAt": now.isoformat(),
                "readAt": None,
            })
            await push_service.send_notification_to_user(
                user_id,
                {
                    "title": "Daily Photo Reminder ✨",
                    "body": "Don't forget to share a moment with your partner today!",
                    "url": "/",
                    "notificationId": notification_id,
                    "type": "daily_reminder",
                }
            )
            self.daily_reminded[user_id] = today_str
            logger.info(f"Sent daily reminder to {user_id}")
        except Exception as e:
            logger.error(f"Daily reminder error for {user_id}: {e}")

    async def _handle_inactivity_reminder(self, user_id, setting, now, push_service):
        try:
            user = await self.users.find_one({"id": user_id})
            if not user or not user.get("coupleId"):
                return
            
            couple = await self.couples.find_one({"id": user["coupleId"]})
            if not couple:
                return
            
            partner_id = couple.get("user2Id") if couple.get("user1Id") == user_id else couple.get("user1Id")
            if not partner_id:
                return
            
            inactivity_hours = setting.get("inactivityHours", 24)
            
            # Find partner's most recent photo
            cursor = self.photos.find(
                {"uploaderId": partner_id, "coupleId": user["coupleId"]},
                {"_id": 0}
            ).sort("createdAt", -1).limit(1)
            partner_photos = await cursor.to_list(length=1)
            
            should_remind = False
            if not partner_photos:
                # Partner never sent — remind once a day max
                last_reminded = self.inactivity_reminded.get(user_id)
                if not last_reminded or (now - last_reminded).total_seconds() > 86400:
                    should_remind = True
            else:
                last_photo_time = datetime.fromisoformat(partner_photos[0]["createdAt"].replace('Z', '+00:00'))
                hours_since = (now - last_photo_time).total_seconds() / 3600
                
                if hours_since >= inactivity_hours:
                    last_reminded = self.inactivity_reminded.get(user_id)
                    # Don't spam - only once per inactivityHours period
                    if not last_reminded or (now - last_reminded).total_seconds() / 3600 >= inactivity_hours:
                        should_remind = True
            
            if should_remind:
                partner_user = await self.users.find_one({"id": partner_id})
                partner_name = partner_user.get("name", "your partner") if partner_user else "your partner"
                
                notification_id = str(uuid.uuid4())
                await self.notifications.insert_one({
                    "id": notification_id,
                    "userId": user_id,
                    "type": "inactivity_reminder",
                    "title": "Time to reconnect 💕",
                    "message": f"{partner_name} hasn't shared a photo in {inactivity_hours} hours. Send them one!",
                    "payload": {},
                    "isRead": False,
                    "createdAt": now.isoformat(),
                    "readAt": None,
                })
                await push_service.send_notification_to_user(
                    user_id,
                    {
                        "title": "Time to reconnect 💕",
                        "body": f"{partner_name} hasn't shared in {inactivity_hours} hours",
                        "url": "/",
                        "notificationId": notification_id,
                        "type": "inactivity_reminder",
                    }
                )
                self.inactivity_reminded[user_id] = now
                logger.info(f"Sent inactivity reminder to {user_id}")
        except Exception as e:
            logger.error(f"Inactivity reminder error for {user_id}: {e}")
