/**
 * RuParked API - JavaScript Frontend Integration Demo
 * This script demonstrates how a React/Vanilla JS frontend would 
 * interact with the Python backend.
 */

const API_BASE = "http://localhost:4000";

async function demo() {
    console.log("🚀 Starting RuParked API Demo...\n");

    // 1. Health Check
    try {
        const healthRes = await fetch(`${API_BASE}/health`);
        const healthData = await healthRes.json();
        console.log("✅ Backend Health:", healthData.status);
    } catch (e) {
        console.error("❌ Backend not running! Run 'python3 main.py' in the backend folder first.");
        return;
    }

    // 2. Sign Up a New User
    const username = `user_${Math.floor(Math.random() * 1000)}`;
    console.log(`\n👤 Signing up as: ${username}...`);
    const signupRes = await fetch(`${API_BASE}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password: "password123" })
    });
    const signupData = await signupRes.json();
    console.log("✅ Signup success! Received Token.");

    const token = signupData.access_token;

    // 3. Get User Info (Me)
    console.log("\n🔑 Fetching user profile with token...");
    const meRes = await fetch(`${API_BASE}/auth/me`, {
        headers: { "Authorization": `Bearer ${token}` }
    });
    const meData = await meRes.json();
    console.log("✅ Profile Data:", meData);

    // 4. Get Azure Maps Config (for the Frontend Map UI)
    console.log("\n🗺️ Fetching Azure Maps Config for UI initialization...");
    const mapsRes = await fetch(`${API_BASE}/navigation/commute/config`);
    const mapsData = await mapsRes.json();
    console.log("✅ Maps Config (Safe for Frontend):", {
        clientId: mapsData.azure_maps_client_id,
        baseUrl: mapsData.azure_maps_base_url
    });

    // 5. Trigger a Spot Alert (Real-time push via ntfy.sh)
    console.log("\n🔔 Sending a Spot Alert (Check ntfy.sh link!)...");
    const alertRes = await fetch(`${API_BASE}/chat/events/spot-alert?user_id=${meData.user_id}&lot_name=Lot48_Livingston`);
    const alertData = await alertRes.json();
    console.log("✅ Notification broadcast successful!");
    console.log("👉 View notification here: https://ntfy.sh/ruparked-alerts-hackathon-2026");

    console.log("\n🎉 Demo completed successfully!");
}

demo();
