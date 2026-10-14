import json
import os
import unittest
from unittest.mock import patch
from discord_notify import send_discord_payload


class Response:
    status=201
    def __enter__(self): return self
    def __exit__(self,*args): return False


class EmbedTests(unittest.TestCase):
    def test_embeds_and_mentions_suppressed(self):
        with (patch.dict(os.environ,{"DISCORD_TOKEN":"placeholder","DISCORD_CHANNEL_ID":"123456789012345678"}),
              patch("discord_notify.request.urlopen", return_value=Response()) as sender):
            ok=send_discord_payload({"embeds":[{"title":"預覽完成","color":3447003}],
                                     "allowed_mentions":{"parse":["everyone"]}})
            self.assertTrue(ok)
            data=json.loads(sender.call_args.args[0].data)
            self.assertEqual(data["allowed_mentions"],{"parse":[]})
            self.assertEqual(data["embeds"][0]["title"],"預覽完成")
            self.assertNotIn("placeholder",str(data))


if __name__ == "__main__":
    unittest.main()
