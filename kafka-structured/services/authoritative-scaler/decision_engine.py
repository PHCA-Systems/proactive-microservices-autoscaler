#!/usr/bin/env python3
"""
Decision Engine
Makes scaling decisions based on model votes
"""

from typing import List, Dict
from collections import Counter


class DecisionEngine:
    def __init__(self, voting_strategy: str = "majority"):
        """
        Initialize decision engine.
        
        Args:
            voting_strategy: Voting strategy ('majority', 'unanimous', 'weighted')
        """
        self.voting_strategy = voting_strategy
        
    def make_decision(self, votes: List[dict]) -> Dict:
        """
        Make a scaling decision based on votes.
        
        Args:
            votes: List of vote dictionaries from ML models
            
        Returns:
            dict: Decision with details
        """
        if not votes:
            return {
                "decision": "NO_OP",
                "reason": "No votes received",
                "votes": [],
                "confidence": 0.0
            }
        
        # Extract predictions and confidences
        predictions = [v["prediction"] for v in votes]
        confidences = [v["confidence"] for v in votes]
        
        # Count votes
        vote_counts = Counter(predictions)
        scale_up_votes = vote_counts.get(1, 0)
        no_action_votes = vote_counts.get(0, 0)
        total_votes = len(votes)
        
        # Apply voting strategy
        if self.voting_strategy == "majority":
            decision = self._majority_vote(scale_up_votes, no_action_votes)
        elif self.voting_strategy == "unanimous":
            decision = self._unanimous_vote(scale_up_votes, total_votes)
        elif self.voting_strategy == "weighted":
            decision = self._weighted_vote(votes)
        else:
            decision = self._majority_vote(scale_up_votes, no_action_votes)
        
        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "decision": decision,
            "votes": votes,
            "scale_up_votes": scale_up_votes,
            "no_action_votes": no_action_votes,
            "total_votes": total_votes,
            "confidence": round(avg_confidence, 4),
            "strategy": self.voting_strategy
        }
    
    def _majority_vote(self, scale_up_votes: int, no_action_votes: int) -> str:
        """Majority voting: decision with most votes wins."""
        if scale_up_votes > no_action_votes:
            return "SCALE_UP"
        elif no_action_votes > scale_up_votes:
            return "NO_OP"
        else:
            # Tie: default to conservative (no action)
            return "NO_OP"
    
    def _unanimous_vote(self, scale_up_votes: int, total_votes: int) -> str:
        """Unanimous voting: all models must agree."""
        if scale_up_votes == total_votes:
            return "SCALE_UP"
        else:
            return "NO_OP"
    
    def _weighted_vote(self, votes: List[dict]) -> str:
        """Weighted voting: weight by confidence."""
        weighted_sum = 0.0
        total_weight = 0.0
        
        for vote in votes:
            prediction = vote["prediction"]
            confidence = vote["confidence"]
            
            # Weight: prediction * confidence
            weighted_sum += prediction * confidence
            total_weight += confidence
        
        if total_weight == 0:
            return "NO_OP"
        
        weighted_avg = weighted_sum / total_weight
        
        # If weighted average > 0.5, scale up
        if weighted_avg > 0.5:
            return "SCALE_UP"
        else:
            return "NO_OP"
    
    def format_decision(self, service: str, decision_result: Dict) -> str:
        """
        Format decision for human-readable output.
        
        Args:
            service: Service name
            decision_result: Decision result from make_decision()
            
        Returns:
            str: Formatted decision string
        """
        lines = []
        lines.append(f"\nService: {service}")
        lines.append("-" * 60)
        
        # Show individual votes
        for vote in decision_result["votes"]:
            model = vote["model"]
            prediction = vote["prediction"]
            confidence = vote["confidence"]
            
            action = "SCALE UP  " if prediction == 1 else "NO ACTION "
            lines.append(f"  {model:20s} -> {action} (confidence: {confidence:.2%})")
        
        # Show decision
        lines.append("-" * 60)
        decision = decision_result["decision"]
        scale_up = decision_result["scale_up_votes"]
        no_action = decision_result["no_action_votes"]
        total = decision_result["total_votes"]
        
        lines.append(f"  DECISION: {decision}")
        lines.append(f"  Vote Count: {scale_up} SCALE UP, {no_action} NO ACTION ({total} total)")
        lines.append(f"  Average Confidence: {decision_result['confidence']:.2%}")
        
        return "\n".join(lines)
