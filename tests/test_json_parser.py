"""Tests for the 4-strategy JSON parser (_parse_llm_response).

Tests use realistic LLM response patterns — no mocking needed.
"""

import json

import pytest

from market_swarm.engine import _parse_llm_response


class TestStrategy1DirectParse:
    def test_clean_json(self):
        text = '{"score": 7, "would_list": true, "key_feedback": "Gut"}'
        result = _parse_llm_response(text)
        assert result["score"] == 7
        assert result["would_list"] is True

    def test_json_with_whitespace(self):
        text = '  \n  {"score": 5, "would_list": false}  \n  '
        result = _parse_llm_response(text)
        assert result["score"] == 5


class TestStrategy2MarkdownBlocks:
    def test_json_code_block(self):
        text = '```json\n{"score": 8, "would_list": true}\n```'
        result = _parse_llm_response(text)
        assert result["score"] == 8

    def test_generic_code_block(self):
        text = '```\n{"score": 6, "would_list": false}\n```'
        result = _parse_llm_response(text)
        assert result["score"] == 6

    def test_json_with_surrounding_text(self):
        text = 'Here is my evaluation:\n{"score": 9, "would_list": true}\nThanks.'
        result = _parse_llm_response(text)
        assert result["score"] == 9


class TestStrategy3UnescapedNewlines:
    def test_newline_in_string_value(self):
        text = """{
    "score": 7,
    "would_list": true,
    "key_feedback": "Good product.
But the price is too high.",
    "objections": []
}"""
        result = _parse_llm_response(text)
        assert result["score"] == 7
        assert "product" in result["key_feedback"].lower()


class TestStrategy4LineReconstruction:
    def test_continuation_lines(self):
        text = """{
    "score": 6,
    "would_list": false,
    "key_feedback": "The product has
    some problems with its
    positioning.",
    "objections": ["Too expensive"],
    "suggestions": ["Lower the price"],
    "detailed_reasoning": "Test"
}"""
        result = _parse_llm_response(text)
        assert result["score"] == 6
        assert "problems" in result["key_feedback"]


class TestEdgeCases:
    def test_nested_json(self):
        text = '{"score": 5, "would_list": true, "key_feedback": "OK", "objections": ["A", "B"]}'
        result = _parse_llm_response(text)
        assert len(result["objections"]) == 2

    def test_no_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_llm_response("No JSON here at all.")

    def test_empty_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_llm_response("")

    def test_realistic_llm_response(self):
        """Simulates a typical Claude response with preamble."""
        text = """Based on my analysis as a buyer, I evaluate the product as follows:

```json
{
    "score": 6.5,
    "would_list": true,
    "key_feedback": "Solid protein bar concept, but the price needs adjusting for the discount channel.",
    "objections": [
        "RRP of 1.99 EUR is too high for the discount-channel target group",
        "Keine Bio-Zertifizierung trotz Trend"
    ],
    "suggestions": [
        "Lower the price to 1.49 EUR or introduce a promo price",
        "Offer multipacks with volume discounts"
    ],
    "price_feedback": "The trade price of 1.10 EUR leaves an acceptable margin, but the RRP will not work in the discount channel.",
    "detailed_reasoning": "The product hits the protein trend, but the price positioning does not fit the discount channel. A hard discounter would expect an RRP below 1.50 EUR in this category."
}
```

I hope this evaluation helps with product development."""
        result = _parse_llm_response(text)
        assert result["score"] == 6.5
        assert result["would_list"] is True
        assert len(result["objections"]) == 2
        assert len(result["suggestions"]) == 2
        assert "1.10" in result["price_feedback"]
