from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Social Module
from services.social.friends import router as friends_router
from services.social.requests import router as requests_router
from services.social.groups import router as groups_router
from services.social.permissions import router as permissions_router
from services.social.availability import router as availability_router
from services.social.overlap import router as overlap_router
from services.social.parkingShare import router as parking_share_router
from services.social.graph import router as graph_router

# Chat Module
from services.chat.messages import router as messages_router
from services.chat.presets import router as presets_router
from services.chat.events import router as events_router

# Student Module
from services.student.classes import router as classes_router
from services.student.clubs import router as clubs_router
from services.student.finals import router as finals_router

# Safety Module
from services.safety.share import router as share_router
from services.safety.sessions import router as sessions_router
from services.safety.emergency import router as emergency_router
from services.safety.pairing import router as pairing_router

# Sustainability Module
from services.sustainability.carpool import router as carpool_router
from services.sustainability.metrics import router as metrics_router
from services.sustainability.challenges import router as challenges_router
from services.sustainability.badges import router as badges_router

# Preferences Module
from services.preferences.social import router as social_prefs_router
from services.preferences.notifications import router as notifications_router

# Trading Module (NEW)
from services.trading.spots import router as trading_spots_router
from services.trading.schedules import router as trading_schedules_router
from services.trading.requests import router as trading_requests_router

# Navigation Module (Converted from TypeScript)
from services.navigation.commute import router as commute_router

app = FastAPI(
    title="RuParked API",
    description="Social, Communication, Safety & Sustainability features for student parking",
    version="1.0.0"
)

# CORS - Allow frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(friends_router)
app.include_router(requests_router)
app.include_router(groups_router)
app.include_router(permissions_router)
app.include_router(availability_router)
app.include_router(overlap_router)
app.include_router(parking_share_router)
app.include_router(messages_router)
app.include_router(presets_router)
app.include_router(events_router)
app.include_router(classes_router)
app.include_router(clubs_router)
app.include_router(finals_router)
app.include_router(share_router)
app.include_router(sessions_router)
app.include_router(emergency_router)
app.include_router(pairing_router)
app.include_router(carpool_router)
app.include_router(metrics_router)
app.include_router(challenges_router)
app.include_router(badges_router)
app.include_router(social_prefs_router)
app.include_router(notifications_router)
app.include_router(trading_spots_router)
app.include_router(trading_schedules_router)
app.include_router(trading_requests_router)
app.include_router(graph_router)
app.include_router(commute_router)


@app.get("/")
async def root():
    return {"message": "RuParked API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
