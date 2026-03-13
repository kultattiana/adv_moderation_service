from fastapi import Depends
from services.auth import AuthService
from services.sellers import SellerService
from services.advertisements import AdvertisementService
from services.moderations import ModerationService
from services.predictions import PredictionService
from typing import Annotated

def auth_service() -> AuthService:
    return AuthService()

def seller_service() -> SellerService:
    return SellerService()

def ad_service() -> AdvertisementService:
    return AdvertisementService()

def mod_service() -> ModerationService:
    return ModerationService()

def pred_service() -> PredictionService:
    return PredictionService()

AuthServiceDepend = Annotated[AuthService, Depends(auth_service)]
SellerServiceDepend = Annotated[SellerService, Depends(seller_service)]
AdServiceDepend = Annotated[AdvertisementService, Depends(ad_service)]
ModServiceDepend = Annotated[ModerationService, Depends(mod_service)]
PredServiceDepend = Annotated[PredictionService, Depends(pred_service)]