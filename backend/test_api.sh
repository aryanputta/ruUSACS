#!/bin/bash
# RuParked API Test Script
# Run this to verify all backend features are working

BASE_URL="http://localhost:8000"
PASS=0
FAIL=0

echo "🚗 RuParked API Test Suite"
echo "=========================="
echo ""

# Function to test endpoint
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" -H "Content-Type: application/json" -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
        echo "✅ $name"
        ((PASS++))
    else
        echo "❌ $name (HTTP $http_code)"
        ((FAIL++))
    fi
}

echo "📍 Core Health Checks"
echo "---------------------"
test_endpoint "API Root" "GET" "/"
test_endpoint "API Health" "GET" "/health"
test_endpoint "Navigation Health" "GET" "/navigation/commute/health"

echo ""
echo "🅿️ Trading - Spots"
echo "------------------"
test_endpoint "List Spot" "POST" "/trading/spots/list" '{"spot_id":"test1","owner_id":"demo_user","lot_name":"Lot 48","spot_number":"B5","available_date":"2026-02-10","start_time":"09:00","end_time":"17:00"}'
test_endpoint "Get Available Spots" "GET" "/trading/spots/available"
test_endpoint "Get My Listings" "GET" "/trading/spots/my-listings/demo_user"

echo ""
echo "📅 Trading - Schedules"
echo "----------------------"
test_endpoint "Save Schedule" "POST" "/trading/schedules/" '{"user_id":"demo_user","semester":"Spring 2026","classes":[{"class_name":"CS111","building":"Hill Center","day":"monday","start_time":"10:00","end_time":"11:20"}]}'
test_endpoint "Get Schedule" "GET" "/trading/schedules/demo_user"
test_endpoint "Find Matches" "GET" "/trading/schedules/demo_user/matches"

echo ""
echo "🙋 Trading - Requests"
echo "---------------------"
test_endpoint "Create Request" "POST" "/trading/requests/" '{"user_id":"demo_user","needed_date":"2026-02-10","start_time":"10:00","end_time":"14:00","preferred_lots":["Lot 48"],"urgency":"medium"}'
test_endpoint "Get Open Requests" "GET" "/trading/requests/"

echo ""
echo "👥 Social - Friend Graph"
echo "------------------------"
test_endpoint "Send Friend Request" "POST" "/social/graph/request/demo_user/friend1" ""
test_endpoint "Get Friends" "GET" "/social/graph/friends/demo_user"
test_endpoint "Get Pending" "GET" "/social/graph/pending/demo_user"

echo ""
echo "🗺️ Navigation"
echo "--------------"
test_endpoint "Parking Lots" "GET" "/navigation/commute/parking-lots"
test_endpoint "Route Calculation" "GET" "/navigation/commute/route?origin_lat=40.5008&origin_lng=-74.4474&dest_lat=40.5230&dest_lng=-74.4580"

echo ""
echo "🌱 Sustainability"
echo "-----------------"
test_endpoint "Carpool Trips" "GET" "/sustainability/carpool/trips"
test_endpoint "Metrics" "POST" "/sustainability/metrics/" '{"user_id":"demo_user"}'

echo ""
echo "=========================="
echo "Results: ✅ $PASS passed, ❌ $FAIL failed"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "🎉 All tests passed! Your API is ready for demo!"
else
    echo "⚠️  Some tests failed. Check the endpoints above."
fi
