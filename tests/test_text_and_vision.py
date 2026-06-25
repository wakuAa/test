import unittest

from PIL import Image, ImageDraw

from wechat_score_bot.models import OcrItem
from wechat_score_bot.ocr import is_a_option_text, normalize_text
from wechat_score_bot.vision import estimate_radio_point, is_selected_near


class TextAndVisionTests(unittest.TestCase):
    def test_normalize_text_handles_chinese_punctuation(self):
        self.assertEqual(normalize_text(" A. A（2.5分） "), "a.a(2.5分)")

    def test_a_option_text_variants(self):
        self.assertTrue(is_a_option_text("A. A (2.5分)"))
        self.assertTrue(is_a_option_text("A.A（2.5分）"))
        self.assertTrue(is_a_option_text("A（2.5分）"))
        self.assertFalse(is_a_option_text("B. B (2分)"))

    def test_estimate_radio_point_is_left_of_text(self):
        item = OcrItem.from_raw_box("A. A (2.5分)", 0.99, [[58, 100], [160, 100], [160, 132], [58, 132]])
        point = estimate_radio_point(item)
        self.assertLess(point[0], item.rect.left)
        self.assertLessEqual(item.rect.top, point[1])
        self.assertLessEqual(point[1], item.rect.bottom)

    def test_selected_blue_detection(self):
        image = Image.new("RGB", (80, 80), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((28, 28, 52, 52), fill=(35, 137, 245))
        self.assertTrue(is_selected_near(image, (40, 40)))

        blank = Image.new("RGB", (80, 80), "white")
        self.assertFalse(is_selected_near(blank, (40, 40)))


if __name__ == "__main__":
    unittest.main()
