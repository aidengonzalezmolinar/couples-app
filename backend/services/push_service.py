import os
import json
import logging
from typing import Dict, Any, List
from py_vapid import Vapid01
import base64
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@memorylink.app")

class PushService:
    def __init__(self, subscriptions_collection):
        self.subscriptions = subscriptions_collection
        
    async def get_user_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.subscriptions.find({"userId": user_id})
        docs = await cursor.to_list(length=None)
        return [doc["subscription"] for doc in docs]

    async def send_notification_to_user(
        self,
        user_id: str,
        payload: Dict[str, Any],
    ) -> None:
        subs = await self.get_user_subscriptions(user_id)
        for sub in subs:
            try:
                await self._send_to_subscription(sub, payload)
            except Exception as exc:
                logger.error(f"Failed to send push notification: {exc}")
                endpoint = sub.get("endpoint")
                if endpoint and "410" in str(exc):
                    await self.subscriptions.delete_one({"subscription.endpoint": endpoint})

    async def _send_to_subscription(
        self,
        subscription: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> None:
        body = json.dumps(payload)
        
        # Use pywebpush-like manual implementation
        from pywebpush import webpush
        
        try:
            # Reconstruct VAPID keys
            private_bytes = base64.urlsafe_b64decode(
                VAPID_PRIVATE_KEY + '=' * (4 - len(VAPID_PRIVATE_KEY) % 4)
            )
            
            vapid_private = ec.derive_private_key(
                int.from_bytes(private_bytes, 'big'),
                ec.SECP256R1()
            )
            
            vapid_private_pem = vapid_private.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            webpush(
                subscription_info=subscription,
                data=body,
                vapid_private_key=vapid_private_pem.decode('utf-8'),
                vapid_claims={"sub": VAPID_SUBJECT}
            )
        except Exception as e:
            logger.error(f"Webpush error: {e}")
            raise
