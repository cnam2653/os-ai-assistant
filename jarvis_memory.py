import redis
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class JarvisMemory:
    """Redis-based memory system for Jarvis"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            print("Redis connected successfully")
        except redis.ConnectionError:
            print("Redis connection failed. Running without memory.")
            self.redis_client = None
    
    def _get_session_id(self, room_id: str = None) -> str:
        """Generate session ID based on room or create default"""
        if room_id:
            return f"session:{room_id}"
        return f"session:default:{datetime.now().strftime('%Y%m%d')}"
    
    # ===== CONVERSATION MEMORY =====
    def store_conversation(self, user_input: str, assistant_response: str, 
                          function_executed: str = None, room_id: str = None):
        """Store conversation in Redis"""
        if not self.redis_client:
            return
            
        session_id = self._get_session_id(room_id)
        conversation_key = f"conversations:{session_id}"
        
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "assistant_response": assistant_response,
            "function_executed": function_executed,
            "session_id": session_id
        }
        
        # Store as list (most recent first)
        self.redis_client.lpush(conversation_key, json.dumps(conversation_entry))
        
        # Keep only last 50 conversations per session
        self.redis_client.ltrim(conversation_key, 0, 49)
        
        # Set expiry for 7 days
        self.redis_client.expire(conversation_key, 604800)
    
    def get_recent_conversations(self, limit: int = 10, room_id: str = None) -> List[Dict]:
        """Get recent conversations for context"""
        if not self.redis_client:
            return []
            
        session_id = self._get_session_id(room_id)
        conversation_key = f"conversations:{session_id}"
        
        conversations = self.redis_client.lrange(conversation_key, 0, limit - 1)
        return [json.loads(conv) for conv in conversations]
    
    def get_conversation_context(self, room_id: str = None) -> str:
        """Get formatted conversation context for the AI"""
        recent_convos = self.get_recent_conversations(5, room_id)
        
        if not recent_convos:
            return ""
            
        context = "Recent conversation history:\n"
        for conv in reversed(recent_convos):  # Show oldest first
            context += f"User: {conv['user_input']}\n"
            context += f"Assistant: {conv['assistant_response']}\n"
            if conv.get('function_executed'):
                context += f"Function executed: {conv['function_executed']}\n"
            context += "---\n"
        
        return context
    
    # ===== CONTEXT MEMORY =====
    def set_context(self, context_type: str, context_data: Any, 
                   expiry_minutes: int = 60, room_id: str = None):
        """Set context (current task, user preferences, etc.)"""
        if not self.redis_client:
            return
            
        session_id = self._get_session_id(room_id)
        context_key = f"context:{session_id}:{context_type}"
        
        context_entry = {
            "data": context_data,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        
        self.redis_client.setex(
            context_key, 
            expiry_minutes * 60, 
            json.dumps(context_entry)
        )
    
    def get_context(self, context_type: str, room_id: str = None) -> Any:
        """Get context data"""
        if not self.redis_client:
            return None
            
        session_id = self._get_session_id(room_id)
        context_key = f"context:{session_id}:{context_type}"
        
        context = self.redis_client.get(context_key)
        if context:
            return json.loads(context)["data"]
        return None
    
    def clear_context(self, context_type: str = None, room_id: str = None):
        """Clear specific context or all contexts"""
        if not self.redis_client:
            return
            
        session_id = self._get_session_id(room_id)
        
        if context_type:
            context_key = f"context:{session_id}:{context_type}"
            self.redis_client.delete(context_key)
        else:
            # Clear all contexts for session
            pattern = f"context:{session_id}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
    
    # ===== COMMAND MEMORY =====
    def store_command_execution(self, command: str, function_name: str, 
                              parameters: Dict, result: Any, room_id: str = None):
        """Store executed command for learning patterns"""
        if not self.redis_client:
            return
            
        session_id = self._get_session_id(room_id)
        command_key = f"commands:{session_id}"
        
        command_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "function_name": function_name,
            "parameters": parameters,
            "result": str(result),
            "session_id": session_id
        }
        
        # Store recent commands
        self.redis_client.lpush(command_key, json.dumps(command_entry))
        self.redis_client.ltrim(command_key, 0, 99)  # Keep last 100
        self.redis_client.expire(command_key, 604800)  # 7 days
    
    def get_recent_commands(self, limit: int = 10, room_id: str = None) -> List[Dict]:
        """Get recent commands for pattern recognition"""
        if not self.redis_client:
            return []
            
        session_id = self._get_session_id(room_id)
        command_key = f"commands:{session_id}"
        
        commands = self.redis_client.lrange(command_key, 0, limit - 1)
        return [json.loads(cmd) for cmd in commands]
    
    def get_command_patterns(self, room_id: str = None) -> str:
        """Get command patterns for AI context"""
        recent_commands = self.get_recent_commands(5, room_id)
        
        if not recent_commands:
            return ""
            
        patterns = "Recent command patterns:\n"
        for cmd in reversed(recent_commands):
            patterns += f"'{cmd['command']}' → {cmd['function_name']}({cmd['parameters']})\n"
        
        return patterns
    
    # ===== USER PREFERENCES =====
    def set_user_preference(self, preference_key: str, value: Any, room_id: str = None):
        """Set user preference (permanent storage)"""
        if not self.redis_client:
            return
            
        session_id = self._get_session_id(room_id)
        pref_key = f"preferences:{session_id}"
        
        self.redis_client.hset(pref_key, preference_key, json.dumps(value))
    
    def get_user_preference(self, preference_key: str, room_id: str = None) -> Any:
        """Get user preference"""
        if not self.redis_client:
            return None
            
        session_id = self._get_session_id(room_id)
        pref_key = f"preferences:{session_id}"
        
        value = self.redis_client.hget(pref_key, preference_key)
        return json.loads(value) if value else None
    
    def get_all_preferences(self, room_id: str = None) -> Dict:
        """Get all user preferences"""
        if not self.redis_client:
            return {}
            
        session_id = self._get_session_id(room_id)
        pref_key = f"preferences:{session_id}"
        
        prefs = self.redis_client.hgetall(pref_key)
        return {k: json.loads(v) for k, v in prefs.items()}
    
    # ===== ANALYTICS =====
    def increment_usage_metric(self, metric_name: str):
        """Track usage metrics"""
        if not self.redis_client:
            return
            
        today = datetime.now().strftime('%Y-%m-%d')
        metric_key = f"metrics:{today}:{metric_name}"
        
        self.redis_client.incr(metric_key)
        self.redis_client.expire(metric_key, 2592000)  # 30 days
    
    def get_usage_stats(self, days: int = 7) -> Dict:
        """Get usage statistics"""
        if not self.redis_client:
            return {}
            
        stats = {}
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            pattern = f"metrics:{date}:*"
            keys = self.redis_client.keys(pattern)
            
            daily_stats = {}
            for key in keys:
                metric_name = key.split(':')[-1]
                daily_stats[metric_name] = int(self.redis_client.get(key) or 0)
            
            stats[date] = daily_stats
        
        return stats
    
    # ===== CACHE MANAGEMENT =====
    def cache_api_response(self, endpoint: str, params: Dict, response: Any, 
                          expiry_minutes: int = 30):
        """Cache API responses to reduce external calls"""
        if not self.redis_client:
            return
            
        # Create cache key from endpoint and parameters
        cache_key = f"cache:{endpoint}:{hashlib.md5(str(sorted(params.items())).encode()).hexdigest()}"
        
        cache_data = {
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "params": params
        }
        
        self.redis_client.setex(
            cache_key, 
            expiry_minutes * 60, 
            json.dumps(cache_data)
        )
    
    def get_cached_response(self, endpoint: str, params: Dict) -> Optional[Any]:
        """Get cached API response"""
        if not self.redis_client:
            return None
            
        cache_key = f"cache:{endpoint}:{hashlib.md5(str(sorted(params.items())).encode()).hexdigest()}"
        cached = self.redis_client.get(cache_key)
        
        if cached:
            return json.loads(cached)["response"]
        return None
    
    # ===== CLEANUP METHODS =====
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data"""
        if not self.redis_client:
            return
            
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # This is a simple cleanup - in production you'd want more sophisticated cleanup
        patterns = ["conversations:*", "commands:*", "context:*"]
        
        for pattern in patterns:
            keys = self.redis_client.keys(pattern)
            for key in keys:
                # Check if key is older than cutoff (this is simplified)
                self.redis_client.expire(key, 86400)  # Set 1 day expiry for old keys
    
    def get_memory_status(self) -> Dict:
        """Get memory system status"""
        if not self.redis_client:
            return {"status": "disabled", "redis_connected": False}
            
        try:
            info = self.redis_client.info()
            return {
                "status": "active",
                "redis_connected": True,
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "keys_stored": self.redis_client.dbsize()
            }
        except:
            return {"status": "error", "redis_connected": False}