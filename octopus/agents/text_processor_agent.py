"""
Text Processing Agent - Example agent for text analysis and processing.
"""

import re
from typing import Dict, List, Optional, Any
from collections import Counter

from octopus.agents.base_agent import BaseAgent
from octopus.router.agents_router import register_agent, agent_interface


@register_agent(
    name="text_processor",
    description="Text processing and analysis agent",
    version="1.0.0",
    tags=["text", "nlp", "analysis"]
)
class TextProcessorAgent(BaseAgent):
    """Agent specialized in text processing and analysis tasks."""
    
    def __init__(self):
        """Initialize the text processor agent."""
        super().__init__(
            name="TextProcessor",
            description="Handles text analysis and processing tasks"
        )
        
    @agent_interface(
        description="Count words in text",
        parameters={
            "text": {"description": "Text to analyze"}
        },
        returns="dict"
    )
    def count_words(self, text: str) -> Dict[str, int]:
        """
        Count words in the given text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with word count statistics
        """
        words = text.split()
        return {
            "total_words": len(words),
            "unique_words": len(set(words)),
            "average_word_length": sum(len(word) for word in words) / len(words) if words else 0
        }
    
    @agent_interface(
        description="Extract keywords from text",
        parameters={
            "text": {"description": "Text to extract keywords from"},
            "top_n": {"description": "Number of top keywords to return"}
        },
        returns="list"
    )
    def extract_keywords(self, text: str, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Extract top keywords from text based on frequency.
        
        Args:
            text: Source text
            top_n: Number of keywords to extract
            
        Returns:
            List of keywords with frequencies
        """
        # Simple keyword extraction based on word frequency
        # Remove punctuation and convert to lowercase
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words (simple list for demo)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were'}
        words = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Count word frequencies
        word_freq = Counter(words)
        
        # Get top keywords
        top_keywords = word_freq.most_common(top_n)
        
        return [
            {"keyword": word, "frequency": freq}
            for word, freq in top_keywords
        ]
    
    @agent_interface(
        description="Analyze text sentiment (simplified)",
        parameters={
            "text": {"description": "Text to analyze sentiment"}
        },
        returns="dict"
    )
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Perform simple sentiment analysis on text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment analysis results
        """
        # Simple sentiment analysis using keyword matching
        positive_words = {'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'happy', 'joy', 'love', 'best'}
        negative_words = {'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'sad', 'angry', 'disappointed', 'poor'}
        
        words = set(re.findall(r'\b\w+\b', text.lower()))
        
        positive_count = len(words.intersection(positive_words))
        negative_count = len(words.intersection(negative_words))
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            sentiment = "neutral"
            confidence = 0.5
        else:
            positive_ratio = positive_count / total_sentiment_words
            if positive_ratio > 0.6:
                sentiment = "positive"
                confidence = positive_ratio
            elif positive_ratio < 0.4:
                sentiment = "negative"
                confidence = 1 - positive_ratio
            else:
                sentiment = "neutral"
                confidence = 0.5
        
        return {
            "sentiment": sentiment,
            "confidence": round(confidence, 2),
            "positive_words": positive_count,
            "negative_words": negative_count
        }
    
    @agent_interface(
        description="Summarize text (extractive summary)",
        parameters={
            "text": {"description": "Text to summarize"},
            "num_sentences": {"description": "Number of sentences in summary"}
        },
        returns="dict"
    )
    def summarize_text(self, text: str, num_sentences: int = 3) -> Dict[str, Any]:
        """
        Create a simple extractive summary of the text.
        
        Args:
            text: Text to summarize
            num_sentences: Number of sentences to include in summary
            
        Returns:
            Summary information
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= num_sentences:
            return {
                "summary": text,
                "original_sentences": len(sentences),
                "summary_sentences": len(sentences)
            }
        
        # Simple scoring based on word frequency
        word_freq = Counter(re.findall(r'\b\w+\b', text.lower()))
        
        # Score sentences
        sentence_scores = []
        for sentence in sentences:
            words = re.findall(r'\b\w+\b', sentence.lower())
            score = sum(word_freq[word] for word in words) / len(words) if words else 0
            sentence_scores.append((sentence, score))
        
        # Sort by score and take top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        summary_sentences = [s[0] for s in sentence_scores[:num_sentences]]
        
        # Reorder sentences as they appeared in original text
        summary_sentences = [s for s in sentences if s in summary_sentences]
        
        return {
            "summary": ". ".join(summary_sentences) + ".",
            "original_sentences": len(sentences),
            "summary_sentences": len(summary_sentences)
        } 