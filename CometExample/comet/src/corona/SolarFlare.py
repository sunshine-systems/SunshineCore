from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class SolarFlare:
    """Message format for inter-Comet communication."""
    timestamp: datetime
    name: str  # Sender's name
    type: str  # Message type
    payload: Any  # Flexible payload
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'datetime': self.timestamp.isoformat(),
            'message_type': self.type,
            'sender': self.name,
            'payload': self.payload
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create SolarFlare from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data['datetime']),
            name=data['sender'],
            type=data['message_type'],
            payload=data.get('payload', {})
        )
