import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from app.controllers.v1 import llm as llm_controller
from app.models.schema import (
    VideoScriptRequest,
    VideoSocialMetadataRequest,
    VideoTermsRequest,
)


class TestLlmController(unittest.TestCase):
    def test_terms_request_bounds_generated_term_count(self):
        """Ordered term prompts must not allocate arbitrary-length examples."""
        self.assertEqual(
            VideoTermsRequest(amount=50, match_materials_to_script=True).amount,
            50,
        )
        for value in (0, -1, 51, None):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    VideoTermsRequest(
                        amount=value, match_materials_to_script=True
                    )

    def test_generate_video_script_forwards_all_prompt_fields(self):
        """文案接口不能丢失高级提示词或段落数量。"""
        body = VideoScriptRequest(
            video_subject="Coffee",
            video_language="en",
            paragraph_number=2,
            video_script_prompt="Friendly tone",
            custom_system_prompt="Return narration only.",
        )

        with patch.object(
            llm_controller.llm,
            "generate_script",
            return_value="Generated script",
        ) as generate:
            response = llm_controller.generate_video_script(SimpleNamespace(headers={'x-task-id': 'req-1'}), body, user=SimpleNamespace(sub='test-user'))

        self.assertEqual(
            response,
            {"status": 200, "data": {"video_script": "Generated script"}},
        )
        generate.assert_called_once_with(
            video_subject="Coffee",
            language="en",
            paragraph_number=2,
            video_script_prompt="Friendly tone",
            custom_system_prompt="Return narration only.",
        )

    def test_generate_video_terms_forwards_order_matching_mode(self):
        """素材顺序匹配开关必须继续传递到关键词生成服务。"""
        body = VideoTermsRequest(
            video_subject="Coffee",
            video_script="First beans, then brewing.",
            amount=4,
            match_materials_to_script=True,
        )

        with patch.object(
            llm_controller.llm,
            "generate_terms",
            return_value=["beans", "brewing"],
        ) as generate:
            response = llm_controller.generate_video_terms(None, body)

        self.assertEqual(
            response,
            {"status": 200, "data": {"video_terms": ["beans", "brewing"]}},
        )
        generate.assert_called_once_with(
            video_subject="Coffee",
            video_script="First beans, then brewing.",
            amount=4,
            match_script_order=True,
        )

    def test_generate_social_metadata_returns_service_payload(self):
        """社交平台元数据接口应保持服务层结果的响应结构。"""
        body = VideoSocialMetadataRequest(
            video_subject="Coffee",
            video_script="Morning coffee.",
            language="en",
            platform="youtube_shorts",
        )
        metadata = {
            "title": "Morning Coffee",
            "caption": "Start the day.",
            "hashtags": ["#coffee"],
        }

        with patch.object(
            llm_controller.llm,
            "generate_social_metadata",
            return_value=metadata,
        ) as generate:
            response = llm_controller.generate_video_social_metadata(None, body)

        self.assertEqual(response, {"status": 200, "data": metadata})
        generate.assert_called_once_with(
            video_subject="Coffee",
            video_script="Morning coffee.",
            language="en",
            platform="youtube_shorts",
        )



class TestLlmRateLimit(unittest.TestCase):
    def _user(self, sub="user-a"):
        return SimpleNamespace(sub=sub)

    def _request(self):
        return SimpleNamespace(headers={"x-task-id": "req-1"})

    def test_script_consumes_one_generation(self):
        body = VideoScriptRequest(video_subject="x")
        with patch.object(llm_controller.rate_limiter, "check_request") as cr, patch.object(llm_controller.rate_limiter, "check_generation") as cg, patch.object(llm_controller.llm, "generate_script", return_value="ok"):
            llm_controller.generate_video_script(self._request(), body, user=self._user())
        self.assertEqual(cr.call_count, 1)
        self.assertEqual(cg.call_count, 1)

    def test_terms_consumes_one_generation(self):
        body = VideoTermsRequest(video_subject="x", video_script="s", amount=3)
        with patch.object(llm_controller.rate_limiter, "check_request") as cr, patch.object(llm_controller.rate_limiter, "check_generation") as cg, patch.object(llm_controller.llm, "generate_terms", return_value=["t"]):
            llm_controller.generate_video_terms(self._request(), body, user=self._user())
        self.assertEqual(cr.call_count, 1)
        self.assertEqual(cg.call_count, 1)

    def test_social_metadata_consumes_one_generation(self):
        body = VideoSocialMetadataRequest(video_subject="x", video_script="s")
        with patch.object(llm_controller.rate_limiter, "check_request") as cr, patch.object(llm_controller.rate_limiter, "check_generation") as cg, patch.object(llm_controller.llm, "generate_social_metadata", return_value={"title": "t"}):
            llm_controller.generate_video_social_metadata(self._request(), body, user=self._user())
        self.assertEqual(cr.call_count, 1)
        self.assertEqual(cg.call_count, 1)


if __name__ == "__main__":
    unittest.main()
