#!/usr/bin/env python3
"""
Vote Aggregator
Collects and aggregates votes from ML models
"""

from collections import defaultdict
from typing import Dict, List
import time


class VoteAggregator:
    def __init__(self, window_seconds: int = 5, expected_models: int = 3):
        """
        Initialize vote aggregator.
        
        Args:
            window_seconds: Time window to collect votes before deciding
            expected_models: Number of models expected to vote
        """
        self.window_seconds = window_seconds
        self.expected_models = expected_models
        self.votes_buffer: Dict[str, List[dict]] = defaultdict(list)
        self.last_decision_time: Dict[str, float] = {}
        self.first_vote_time: Dict[str, float] = {}  # Track when first vote arrives
        
    def add_vote(self, vote: dict):
        """Add a vote to the buffer."""
        service = vote.get("service", "unknown")
        
        # Track when first vote arrives for this service
        if service not in self.first_vote_time:
            self.first_vote_time[service] = time.time()
        
        self.votes_buffer[service].append(vote)
    
    def should_make_decision(self, service: str) -> bool:
        """
        Check if we should make a decision for a service.
        
        Returns True if:
        - We have votes from all expected models, OR
        - The time window has elapsed since the first vote
        """
        if service not in self.votes_buffer:
            return False
        
        votes = self.votes_buffer[service]
        
        # Check if we have all votes
        if len(votes) >= self.expected_models:
            return True
        
        # Check if time window elapsed since FIRST vote
        if service in self.first_vote_time:
            elapsed = time.time() - self.first_vote_time[service]
            if elapsed >= self.window_seconds and len(votes) > 0:
                return True
        
        return False
    
    def get_votes_for_service(self, service: str) -> List[dict]:
        """Get all votes for a service and clear the buffer."""
        votes = self.votes_buffer.get(service, [])
        
        # Clear buffer
        if service in self.votes_buffer:
            del self.votes_buffer[service]
        
        # Clear first vote time
        if service in self.first_vote_time:
            del self.first_vote_time[service]
        
        # Update last decision time
        self.last_decision_time[service] = time.time()
        
        return votes
    
    def get_pending_services(self) -> List[str]:
        """Get list of services with pending votes."""
        return list(self.votes_buffer.keys())
