"""
Friendship Graph Service
Two-way bidirectional friendship connections
Uses graph structure to track friend relationships
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Set, Dict
from datetime import datetime
from enum import Enum
from collections import defaultdict

router = APIRouter(prefix="/social/graph", tags=["Social - Friend Graph"])


class FriendshipStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"


class FriendConnection(BaseModel):
    user_id: str
    friend_id: str
    status: FriendshipStatus = FriendshipStatus.PENDING
    created_at: datetime = None
    accepted_at: datetime = None


class UserNode(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    friends: List[str] = []
    pending_sent: List[str] = []
    pending_received: List[str] = []
    blocked: List[str] = []


# ============================================================
# FRIENDSHIP GRAPH (Two-way connections)
# ============================================================
# Using adjacency list representation for the graph
# When a friendship is accepted, both users are added to each other's friend list

class FriendshipGraph:
    def __init__(self):
        # adjacency list: user_id -> set of friend_ids
        self.friends: Dict[str, Set[str]] = defaultdict(set)
        # pending requests: from_user -> set of to_users
        self.pending: Dict[str, Set[str]] = defaultdict(set)
        # blocked users: user -> set of blocked users
        self.blocked: Dict[str, Set[str]] = defaultdict(set)
        # user metadata
        self.users: Dict[str, dict] = {}
    
    def add_user(self, user_id: str, display_name: str = None):
        """Add a user to the graph"""
        if user_id not in self.users:
            self.users[user_id] = {
                "user_id": user_id,
                "display_name": display_name or user_id,
                "created_at": datetime.now().isoformat()
            }
    
    def send_request(self, from_user: str, to_user: str) -> dict:
        """Send a friend request (one-way until accepted)"""
        self.add_user(from_user)
        self.add_user(to_user)
        
        # Check if already friends
        if to_user in self.friends[from_user]:
            return {"status": "already_friends"}
        
        # Check if blocked
        if from_user in self.blocked[to_user]:
            return {"status": "blocked"}
        
        # Check if request already sent
        if to_user in self.pending[from_user]:
            return {"status": "already_pending"}
        
        # Check if they sent us a request (auto-accept)
        if from_user in self.pending[to_user]:
            return self.accept_request(to_user, from_user)
        
        self.pending[from_user].add(to_user)
        return {"status": "request_sent", "from": from_user, "to": to_user}
    
    def accept_request(self, user_id: str, from_user: str) -> dict:
        """Accept a friend request - creates TWO-WAY connection"""
        if from_user not in self.pending or user_id not in self.pending[from_user]:
            # Check reverse
            if user_id not in self.pending or from_user not in self.pending[user_id]:
                return {"status": "no_pending_request"}
            # It's the reverse direction
            user_id, from_user = from_user, user_id
        
        # Remove from pending
        self.pending[from_user].discard(user_id)
        
        # Add TWO-WAY connection (bidirectional)
        self.friends[user_id].add(from_user)
        self.friends[from_user].add(user_id)
        
        return {
            "status": "accepted",
            "connection": [user_id, from_user],
            "is_bidirectional": True
        }
    
    def decline_request(self, user_id: str, from_user: str) -> dict:
        """Decline a friend request"""
        self.pending[from_user].discard(user_id)
        return {"status": "declined"}
    
    def remove_friend(self, user_id: str, friend_id: str) -> dict:
        """Remove a friend - removes BOTH directions"""
        self.friends[user_id].discard(friend_id)
        self.friends[friend_id].discard(user_id)
        return {"status": "removed", "was_bidirectional": True}
    
    def block_user(self, user_id: str, block_id: str) -> dict:
        """Block a user - also removes friendship"""
        self.remove_friend(user_id, block_id)
        self.blocked[user_id].add(block_id)
        self.pending[block_id].discard(user_id)
        return {"status": "blocked"}
    
    def unblock_user(self, user_id: str, block_id: str) -> dict:
        """Unblock a user"""
        self.blocked[user_id].discard(block_id)
        return {"status": "unblocked"}
    
    def get_friends(self, user_id: str) -> List[str]:
        """Get all friends of a user"""
        return list(self.friends[user_id])
    
    def get_pending_received(self, user_id: str) -> List[str]:
        """Get pending requests received by user"""
        received = []
        for from_user, to_users in self.pending.items():
            if user_id in to_users:
                received.append(from_user)
        return received
    
    def get_pending_sent(self, user_id: str) -> List[str]:
        """Get pending requests sent by user"""
        return list(self.pending[user_id])
    
    def are_friends(self, user1: str, user2: str) -> bool:
        """Check if two users are friends (bidirectional check)"""
        return user2 in self.friends[user1] and user1 in self.friends[user2]
    
    def get_mutual_friends(self, user1: str, user2: str) -> List[str]:
        """Find mutual friends between two users"""
        friends1 = self.friends[user1]
        friends2 = self.friends[user2]
        return list(friends1 & friends2)
    
    def get_friend_suggestions(self, user_id: str, limit: int = 10) -> List[dict]:
        """Suggest friends based on mutual connections"""
        my_friends = self.friends[user_id]
        suggestions = defaultdict(int)
        
        # Count friends of friends
        for friend in my_friends:
            for fof in self.friends[friend]:
                if fof != user_id and fof not in my_friends:
                    if fof not in self.blocked[user_id]:
                        suggestions[fof] += 1
        
        # Sort by mutual friend count
        sorted_suggestions = sorted(suggestions.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"user_id": uid, "mutual_friends": count}
            for uid, count in sorted_suggestions[:limit]
        ]
    
    def get_connection_path(self, user1: str, user2: str, max_depth: int = 4) -> List[str]:
        """Find shortest path between two users (BFS)"""
        if user1 == user2:
            return [user1]
        
        visited = {user1}
        queue = [[user1]]
        
        while queue:
            path = queue.pop(0)
            if len(path) > max_depth:
                return []
            
            current = path[-1]
            for friend in self.friends[current]:
                if friend == user2:
                    return path + [user2]
                if friend not in visited:
                    visited.add(friend)
                    queue.append(path + [friend])
        
        return []


# Global graph instance
friendship_graph = FriendshipGraph()


# ============================================================
# API ENDPOINTS
# ============================================================

@router.post("/users/{user_id}")
async def register_user(user_id: str, display_name: Optional[str] = None):
    """Register a user in the friend graph"""
    friendship_graph.add_user(user_id, display_name)
    return {"message": "User registered", "user_id": user_id}


@router.post("/request/{from_user}/{to_user}")
async def send_friend_request(from_user: str, to_user: str):
    """Send a friend request"""
    result = friendship_graph.send_request(from_user, to_user)
    return result


@router.post("/accept/{user_id}/{from_user}")
async def accept_friend_request(user_id: str, from_user: str):
    """Accept a friend request - creates bidirectional connection"""
    result = friendship_graph.accept_request(user_id, from_user)
    return result


@router.post("/decline/{user_id}/{from_user}")
async def decline_friend_request(user_id: str, from_user: str):
    """Decline a friend request"""
    result = friendship_graph.decline_request(user_id, from_user)
    return result


@router.delete("/unfriend/{user_id}/{friend_id}")
async def remove_friend(user_id: str, friend_id: str):
    """Remove a friend (removes both directions)"""
    result = friendship_graph.remove_friend(user_id, friend_id)
    return result


@router.get("/friends/{user_id}")
async def get_friends(user_id: str):
    """Get all friends of a user"""
    friends = friendship_graph.get_friends(user_id)
    return {"user_id": user_id, "friends": friends, "count": len(friends)}


@router.get("/pending/{user_id}")
async def get_pending_requests(user_id: str):
    """Get all pending friend requests"""
    received = friendship_graph.get_pending_received(user_id)
    sent = friendship_graph.get_pending_sent(user_id)
    return {
        "user_id": user_id,
        "received": received,
        "sent": sent
    }


@router.get("/check/{user1}/{user2}")
async def check_friendship(user1: str, user2: str):
    """Check if two users are friends"""
    are_friends = friendship_graph.are_friends(user1, user2)
    return {
        "user1": user1,
        "user2": user2,
        "are_friends": are_friends,
        "is_bidirectional": are_friends
    }


@router.get("/mutual/{user1}/{user2}")
async def get_mutual_friends(user1: str, user2: str):
    """Get mutual friends between two users"""
    mutual = friendship_graph.get_mutual_friends(user1, user2)
    return {
        "user1": user1,
        "user2": user2,
        "mutual_friends": mutual,
        "count": len(mutual)
    }


@router.get("/suggestions/{user_id}")
async def get_friend_suggestions(user_id: str, limit: int = 10):
    """Get friend suggestions based on mutual connections"""
    suggestions = friendship_graph.get_friend_suggestions(user_id, limit)
    return {"user_id": user_id, "suggestions": suggestions}


@router.get("/path/{user1}/{user2}")
async def find_connection_path(user1: str, user2: str):
    """Find the shortest connection path between two users"""
    path = friendship_graph.get_connection_path(user1, user2)
    return {
        "user1": user1,
        "user2": user2,
        "path": path,
        "degrees_of_separation": len(path) - 1 if path else -1
    }


@router.post("/block/{user_id}/{block_id}")
async def block_user(user_id: str, block_id: str):
    """Block a user"""
    result = friendship_graph.block_user(user_id, block_id)
    return result


@router.post("/unblock/{user_id}/{block_id}")
async def unblock_user(user_id: str, block_id: str):
    """Unblock a user"""
    result = friendship_graph.unblock_user(user_id, block_id)
    return result


@router.get("/stats/{user_id}")
async def get_user_stats(user_id: str):
    """Get friendship stats for a user"""
    friends = friendship_graph.get_friends(user_id)
    pending_received = friendship_graph.get_pending_received(user_id)
    pending_sent = friendship_graph.get_pending_sent(user_id)
    
    return {
        "user_id": user_id,
        "friend_count": len(friends),
        "pending_received_count": len(pending_received),
        "pending_sent_count": len(pending_sent),
        "blocked_count": len(friendship_graph.blocked[user_id])
    }
