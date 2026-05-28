from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
import random
import string

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from services.storage_service import init_storage, put_object, get_object, generate_photo_path
from services.push_service import PushService
from services.scheduler import ReminderScheduler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from contextlib import asynccontextmanager
import os
from motor.motor_asyncio import AsyncIOMotorClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_url = os.getenv("MONGO_URL")
    db_name = os.getenv("DB_NAME", "couples_app")

    if mongo_url:
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]

        app.state.mongo_client = client
        app.state.db = db
        app.state.users = db.get_collection("users")
        app.state.couples = db.get_collection("couples")
        app.state.photos = db.get_collection("photos")
        app.state.notifications = db.get_collection("notifications")
        app.state.subscriptions = db.get_collection("push_subscriptions")
        app.state.reminders = db.get_collection("reminders")
        app.state.notification_state = db.get_collection("userNotificationState")
        app.state.messages = db.get_collection("messages")
        app.state.settings = db.get_collection("user_settings")

        print("✅ MongoDB connected")

    else:
        print("⚠️ MongoDB NOT found — running in MEMORY MODE")

        class MemoryDB:
            pass

        db = MemoryDB()

        # fake collections (so code doesn't crash)
        app.state.db = db
        app.state.users = {}
        app.state.couples = {}
        app.state.photos = {}
        app.state.notifications = {}
        app.state.subscriptions = {}
        app.state.reminders = {}
        app.state.notification_state = {}
        app.state.messages = {}
        app.state.settings = {}

    yield

    # shutdown cleanup
    if hasattr(app.state, "mongo_client"):
        app.state.mongo_client.close()
    
    # Storage will be initialized on first use
    logger.info("Storage ready (will initialize on first use)")
    
    # Start reminder scheduler
    def push_service_factory():
        return PushService(app.state.subscriptions)
    
    scheduler = ReminderScheduler(
        app.state.reminders,
        app.state.subscriptions,
        app.state.notifications,
        push_service_factory,
        couples_collection=app.state.couples,
        users_collection=app.state.users,
        photos_collection=app.state.photos,
        settings_collection=app.state.settings,
    )
    scheduler.start()
    app.state.scheduler = scheduler
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    client.close()

app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    coupleId: Optional[str] = None
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CreateUserRequest(BaseModel):
    name: str

class JoinCoupleRequest(BaseModel):
    pairCode: str
    userId: str

class Photo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    uploaderId: str
    coupleId: str
    storagePath: str
    caption: Optional[str] = None
    reactions: List[dict] = Field(default_factory=list)
    createdAt: str

class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    userId: str
    type: str
    title: str
    message: str
    payload: dict
    isRead: bool
    createdAt: str
    readAt: Optional[str] = None

class PushSubscriptionModel(BaseModel):
    endpoint: str
    expirationTime: Optional[float] = None
    keys: dict

class ReminderCreate(BaseModel):
    scheduledAt: str
    message: str
    type: str = "custom"

# Auth Routes
@api_router.post("/auth/create-user", response_model=User)
async def create_user(req: CreateUserRequest):
    user_dict = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "coupleId": None,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await app.state.users.insert_one(user_dict)
    return User(**user_dict)

@api_router.post("/auth/generate-code")
async def generate_pairing_code(userId: str = Query(...)):
    # Generate 6-digit code
    code = ''.join(random.choices(string.digits, k=6))
    
    # Check if user already has a couple
    user = await app.state.users.find_one({"id": userId})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("coupleId"):
        couple = await app.state.couples.find_one({"id": user["coupleId"]})
        if couple:
            return {"pairCode": couple.get("pairCode"), "existing": True}
    
    # Create couple with code
    couple_id = str(uuid.uuid4())
    couple_doc = {
        "id": couple_id,
        "pairCode": code,
        "user1Id": userId,
        "user2Id": None,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await app.state.couples.insert_one(couple_doc)
    
    # Update user
    await app.state.users.update_one(
        {"id": userId},
        {"$set": {"coupleId": couple_id}}
    )
    
    return {"pairCode": code, "existing": False}

@api_router.post("/auth/join-couple")
async def join_couple(req: JoinCoupleRequest):
    # Find couple by code
    couple = await app.state.couples.find_one({"pairCode": req.pairCode})
    if not couple:
        raise HTTPException(status_code=404, detail="Invalid pairing code")
    
    if couple.get("user2Id"):
        raise HTTPException(status_code=400, detail="This pairing code is already used")
    
    couple_id = couple["id"]
    
    # Update couple
    await app.state.couples.update_one(
        {"id": couple_id},
        {"$set": {"user2Id": req.userId}}
    )
    
    # Update user
    await app.state.users.update_one(
        {"id": req.userId},
        {"$set": {"coupleId": couple_id}}
    )
    
    return {"success": True, "coupleId": couple_id}

@api_router.get("/auth/me")
async def get_current_user(userId: str = Query(...)):
    user = await app.state.users.find_one({"id": userId}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@api_router.get("/auth/partner")
async def get_partner(userId: str = Query(...)):
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        return None
    
    couple = await app.state.couples.find_one({"id": user["coupleId"]})
    if not couple:
        return None
    
    partner_id = couple.get("user2Id") if couple.get("user1Id") == userId else couple.get("user1Id")
    if not partner_id:
        return None
    
    partner = await app.state.users.find_one({"id": partner_id}, {"_id": 0})
    return partner

# Photo Routes
@api_router.post("/photos/upload")
async def upload_photo(
    file: UploadFile = File(...),
    userId: str = Form(...),
    caption: Optional[str] = Form(None)
):
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        raise HTTPException(status_code=400, detail="User not in a couple")
    
    couple_id = user["coupleId"]
    
    # Upload to storage
    content = await file.read()
    path = generate_photo_path(userId, file.filename)
    result = put_object(path, content, file.content_type or "image/jpeg")
    
    # Store in DB
    photo_doc = {
        "id": str(uuid.uuid4()),
        "uploaderId": userId,
        "coupleId": couple_id,
        "storagePath": result["path"],
        "caption": caption,
        "reactions": [],
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await app.state.photos.insert_one(photo_doc)
    
    # Get partner
    couple = await app.state.couples.find_one({"id": couple_id})
    partner_id = couple.get("user2Id") if couple.get("user1Id") == userId else couple.get("user1Id")
    
    if partner_id:
        # Create notification
        notification_id = str(uuid.uuid4())
        notif_doc = {
            "id": notification_id,
            "userId": partner_id,
            "type": "photo_upload",
            "title": "New photo from your partner",
            "message": f"{user['name']} shared a new photo with you",
            "payload": {"photoId": photo_doc["id"]},
            "isRead": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "readAt": None
        }
        await app.state.notifications.insert_one(notif_doc)
        
        # Send push notification
        push_service = PushService(app.state.subscriptions)
        await push_service.send_notification_to_user(
            partner_id,
            {
                "title": notif_doc["title"],
                "body": notif_doc["message"],
                "url": f"/photos",
                "notificationId": notification_id,
                "type": "photo_upload",
                "icon": "/logo192.png"
            }
        )
    
    return {"photoId": photo_doc["id"]}

@api_router.get("/photos")
async def get_photos(userId: str = Query(...)):
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        return []
    
    cursor = app.state.photos.find(
        {"coupleId": user["coupleId"]},
        {"_id": 0}
    ).sort("createdAt", -1)
    photos = await cursor.to_list(length=100)
    return photos

@api_router.get("/photos/{photo_id}/download")
async def download_photo(photo_id: str, userId: str = Query(...)):
    photo = await app.state.photos.find_one({"id": photo_id})
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    user = await app.state.users.find_one({"id": userId})
    if not user or user.get("coupleId") != photo["coupleId"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    data, content_type = get_object(photo["storagePath"])
    return Response(content=data, media_type=content_type)

@api_router.post("/photos/{photo_id}/react")
async def react_to_photo(photo_id: str, userId: str = Query(...), emoji: str = Query(...)):
    photo = await app.state.photos.find_one({"id": photo_id})
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    user = await app.state.users.find_one({"id": userId})
    if not user or user.get("coupleId") != photo["coupleId"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    reaction = {
        "userId": userId,
        "emoji": emoji,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await app.state.photos.update_one(
        {"id": photo_id},
        {"$push": {"reactions": reaction}}
    )
    
    return {"success": True}

# Notification Routes
@api_router.get("/notifications", response_model=List[Notification])
async def get_notifications(userId: str = Query(...)):
    cursor = app.state.notifications.find(
        {"userId": userId},
        {"_id": 0}
    ).sort("createdAt", -1)
    notifications = await cursor.to_list(length=100)
    
    for notif in notifications:
        notif["id"] = notif.get("id", str(uuid.uuid4()))
    
    return notifications

@api_router.patch("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, userId: str = Query(...)):
    result = await app.state.notifications.update_one(
        {"id": notif_id, "userId": userId},
        {"$set": {"isRead": True, "readAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True}

@api_router.get("/notifications/unread-count")
async def get_unread_count(userId: str = Query(...)):
    count = await app.state.notifications.count_documents(
        {"userId": userId, "isRead": False}
    )
    return {"count": count}

# Push Routes
@api_router.post("/push/subscribe")
async def subscribe_to_push(subscription: PushSubscriptionModel, userId: str = Query(...)):
    existing = await app.state.subscriptions.find_one(
        {"userId": userId, "subscription.endpoint": subscription.endpoint}
    )
    
    if existing:
        await app.state.subscriptions.update_one(
            {"_id": existing["_id"]},
            {"$set": {"subscription": subscription.model_dump()}}
        )
    else:
        await app.state.subscriptions.insert_one(
            {"userId": userId, "subscription": subscription.model_dump()}
        )
    
    return {"status": "ok"}

@api_router.get("/push/vapid-public-key")
async def get_vapid_public_key():
    return {"publicKey": os.environ.get("VAPID_PUBLIC_KEY")}

# Reminder Routes
@api_router.post("/reminders")
async def create_reminder(reminder: ReminderCreate, userId: str = Query(...)):
    doc = {
        "userId": userId,
        "scheduledAt": datetime.fromisoformat(reminder.scheduledAt.replace('Z', '+00:00')),
        "message": reminder.message,
        "type": reminder.type,
        "processed": False,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await app.state.reminders.insert_one(doc)
    return {"status": "scheduled"}

@api_router.get("/reminders")
async def get_reminders(userId: str = Query(...)):
    cursor = app.state.reminders.find(
        {"userId": userId},
        {"_id": 0}
    ).sort("scheduledAt", 1)
    reminders = await cursor.to_list(length=100)
    
    for rem in reminders:
        if isinstance(rem.get("scheduledAt"), datetime):
            rem["scheduledAt"] = rem["scheduledAt"].isoformat()
    
    return reminders

# Comment Routes
class CommentCreate(BaseModel):
    text: str

@api_router.post("/photos/{photo_id}/comment")
async def add_comment(photo_id: str, comment: CommentCreate, userId: str = Query(...)):
    photo = await app.state.photos.find_one({"id": photo_id})
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    user = await app.state.users.find_one({"id": userId})
    if not user or user.get("coupleId") != photo["coupleId"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    comment_doc = {
        "id": str(uuid.uuid4()),
        "userId": userId,
        "userName": user["name"],
        "text": comment.text,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await app.state.photos.update_one(
        {"id": photo_id},
        {"$push": {"comments": comment_doc}}
    )
    
    # Notify the other person if comment is by partner
    if userId != photo["uploaderId"]:
        notif_id = str(uuid.uuid4())
        await app.state.notifications.insert_one({
            "id": notif_id,
            "userId": photo["uploaderId"],
            "type": "comment",
            "title": f"{user['name']} commented on your photo",
            "message": comment.text[:80],
            "payload": {"photoId": photo_id},
            "isRead": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "readAt": None
        })
        push_service = PushService(app.state.subscriptions)
        await push_service.send_notification_to_user(
            photo["uploaderId"],
            {
                "title": f"{user['name']} commented",
                "body": comment.text[:80],
                "url": "/gallery",
                "notificationId": notif_id,
                "type": "comment"
            }
        )
    
    return {k: v for k, v in comment_doc.items() if k != "_id"}

# Message Routes
class MessageCreate(BaseModel):
    text: str

@api_router.post("/messages")
async def send_message(message: MessageCreate, userId: str = Query(...)):
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        raise HTTPException(status_code=400, detail="User not in a couple")
    
    couple = await app.state.couples.find_one({"id": user["coupleId"]})
    partner_id = couple.get("user2Id") if couple.get("user1Id") == userId else couple.get("user1Id")
    
    msg_doc = {
        "id": str(uuid.uuid4()),
        "coupleId": user["coupleId"],
        "senderId": userId,
        "senderName": user["name"],
        "text": message.text,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "readBy": [userId]
    }
    await app.state.messages.insert_one(msg_doc)
    # Build a clean response (insert_one mutates msg_doc to add _id)
    response_msg = {k: v for k, v in msg_doc.items() if k != "_id"}
    
    if partner_id:
        # Notification
        notif_id = str(uuid.uuid4())
        await app.state.notifications.insert_one({
            "id": notif_id,
            "userId": partner_id,
            "type": "message",
            "title": f"New message from {user['name']}",
            "message": message.text[:80],
            "payload": {"messageId": msg_doc["id"]},
            "isRead": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "readAt": None
        })
        push_service = PushService(app.state.subscriptions)
        await push_service.send_notification_to_user(
            partner_id,
            {
                "title": f"💌 {user['name']}",
                "body": message.text[:80],
                "url": "/chat",
                "notificationId": notif_id,
                "type": "message"
            }
        )
    
    return response_msg

@api_router.get("/messages")
async def get_messages(userId: str = Query(...)):
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        return []
    
    cursor = app.state.messages.find(
        {"coupleId": user["coupleId"]},
        {"_id": 0}
    ).sort("createdAt", 1)
    messages = await cursor.to_list(length=500)
    return messages

@api_router.post("/messages/mark-read")
async def mark_messages_read(userId: str = Query(...)):
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        return {"success": True}
    
    await app.state.messages.update_many(
        {"coupleId": user["coupleId"], "readBy": {"$ne": userId}},
        {"$addToSet": {"readBy": userId}}
    )
    return {"success": True}

@api_router.get("/messages/unread-count")
async def get_unread_messages(userId: str = Query(...)):
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        return {"count": 0}
    
    count = await app.state.messages.count_documents({
        "coupleId": user["coupleId"],
        "senderId": {"$ne": userId},
        "readBy": {"$ne": userId}
    })
    return {"count": count}

# Streak Routes
MILESTONES = [3, 7, 14, 30, 50, 100, 200, 365, 500, 1000]

@api_router.get("/streak")
async def get_streak(userId: str = Query(...)):
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        return {"streak": 0, "todayUserSent": False, "todayPartnerSent": False, "atRisk": False, "newMilestone": None}
    
    couple_id = user["coupleId"]
    couple = await app.state.couples.find_one({"id": couple_id})
    partner_id = couple.get("user2Id") if couple.get("user1Id") == userId else couple.get("user1Id")
    
    # Get all photos for the couple, sorted by date desc
    cursor = app.state.photos.find({"coupleId": couple_id}, {"_id": 0}).sort("createdAt", -1)
    photos = await cursor.to_list(length=2000)
    
    # Group photos by date and uploaderId
    from collections import defaultdict
    days = defaultdict(set)
    for p in photos:
        date_str = p["createdAt"][:10]  # YYYY-MM-DD
        days[date_str].add(p["uploaderId"])
    
    # Streak: consecutive days where BOTH users have sent at least one photo
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    today_user_sent = userId in days.get(today, set())
    today_partner_sent = partner_id and partner_id in days.get(today, set())
    
    # Count consecutive days going back from today (or yesterday if today incomplete)
    streak = 0
    check_date = datetime.now(timezone.utc)
    
    # If today both sent, count it; else start from yesterday
    if today_user_sent and today_partner_sent:
        streak = 1
        check_date = check_date - timedelta(days=1)
    
    while True:
        date_str = check_date.strftime("%Y-%m-%d")
        uploaders = days.get(date_str, set())
        if userId in uploaders and partner_id and partner_id in uploaders:
            streak += 1
            check_date = check_date - timedelta(days=1)
        else:
            break
        if streak > 1000:  # safety
            break
    
    # Check for new milestone (one not yet celebrated)
    celebrated = set(couple.get("celebratedMilestones", []))
    new_milestone = None
    if streak in MILESTONES and streak not in celebrated:
        new_milestone = streak
    
    # Calculate at-risk status:
    # streak > 0 AND yesterday both sent AND today missing at least one upload
    # AND it's later in the day (past 4pm UTC by default, gives time for partner)
    at_risk = False
    yesterday_uploaders = days.get(yesterday, set())
    yesterday_complete = userId in yesterday_uploaders and partner_id and partner_id in yesterday_uploaders
    
    if streak > 0 and yesterday_complete:
        if not today_user_sent or not today_partner_sent:
            current_hour = datetime.now(timezone.utc).hour
            if current_hour >= 18:  # Past 6pm UTC (matches scheduler window)
                at_risk = True
    
    return {
        "streak": streak,
        "todayUserSent": today_user_sent,
        "todayPartnerSent": bool(today_partner_sent),
        "atRisk": at_risk,
        "newMilestone": new_milestone,
    }

@api_router.post("/streak/celebrate")
async def celebrate_milestone(milestone: int = Query(...), userId: str = Query(...)):
    """Mark a milestone as celebrated for this couple so we don't show it again."""
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        raise HTTPException(status_code=400, detail="User not in a couple")
    
    await app.state.couples.update_one(
        {"id": user["coupleId"]},
        {"$addToSet": {"celebratedMilestones": milestone}}
    )
    return {"success": True}

@api_router.post("/streak/save")
async def save_streak(userId: str = Query(...)):
    """User pings their partner urgently to save the streak."""
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        raise HTTPException(status_code=400, detail="User not in a couple")
    
    couple = await app.state.couples.find_one({"id": user["coupleId"]})
    partner_id = couple.get("user2Id") if couple.get("user1Id") == userId else couple.get("user1Id")
    
    if not partner_id:
        raise HTTPException(status_code=400, detail="No partner connected")
    
    # Create notification for partner
    notif_id = str(uuid.uuid4())
    await app.state.notifications.insert_one({
        "id": notif_id,
        "userId": partner_id,
        "type": "streak_save",
        "title": "🔥 Your streak is at risk!",
        "message": f"{user['name']} is asking you to send a photo to save your streak!",
        "payload": {},
        "isRead": False,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "readAt": None
    })
    
    push_service = PushService(app.state.subscriptions)
    await push_service.send_notification_to_user(
        partner_id,
        {
            "title": "🔥 Save the streak!",
            "body": f"{user['name']} needs you to send a photo NOW",
            "url": "/",
            "notificationId": notif_id,
            "type": "streak_save",
        }
    )
    
    return {"success": True}

# Memory Routes (on this day)
@api_router.get("/photos/memories")
async def get_memories(userId: str = Query(...)):
    user = await app.state.users.find_one({"id": userId})
    if not user or not user.get("coupleId"):
        return []
    
    today = datetime.now(timezone.utc)
    target_month = today.month
    target_day = today.day
    
    cursor = app.state.photos.find({"coupleId": user["coupleId"]}, {"_id": 0})
    all_photos = await cursor.to_list(length=2000)
    
    memories = []
    for p in all_photos:
        try:
            d = datetime.fromisoformat(p["createdAt"].replace('Z', '+00:00'))
            if d.month == target_month and d.day == target_day and d.year < today.year:
                memories.append(p)
        except Exception:
            continue
    
    memories.sort(key=lambda x: x["createdAt"], reverse=True)
    return memories

# Settings Routes
class UserSettings(BaseModel):
    dailyReminderEnabled: bool = False
    dailyReminderTime: str = "20:00"  # HH:MM 24h format
    inactivityReminderEnabled: bool = False
    inactivityHours: int = 24

@api_router.get("/settings")
async def get_settings(userId: str = Query(...)):
    settings = await app.state.settings.find_one({"userId": userId}, {"_id": 0})
    if not settings:
        return UserSettings().model_dump()
    return {k: v for k, v in settings.items() if k != "userId"}

@api_router.put("/settings")
async def update_settings(settings: UserSettings, userId: str = Query(...)):
    doc = settings.model_dump()
    doc["userId"] = userId
    doc["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    await app.state.settings.update_one(
        {"userId": userId},
        {"$set": doc},
        upsert=True
    )
    return {"success": True}

# Test route
@api_router.get("/")
async def root():
    return {"message": "Memory Link API"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Backend is running 🚀"}
    
