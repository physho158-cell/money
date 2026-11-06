# Myanmar Video Dubbing Telegram Bot

YouTube Shorts / YouTube video link သို့မဟုတ် Telegram တွင် တင်ထားသော video ကို လက်ခံပြီး၊ မူရင်းအသံအားလုံးကို ဖယ်ထုတ်ကာ **မြန်မာလို ဘာသာပြန်ထားသော AI အသံအသစ်ပါသော MP4** ကို ပြန်ပေးသော Telegram bot ဖြစ်သည်။

## လုပ်ဆောင်ပုံ

1. `yt-dlp` ဖြင့် YouTube video ကို ဒေါင်းလုဒ်လုပ်သည် (Telegram upload ကိုလည်း လက်ခံသည်)။
2. `ffmpeg` ဖြင့် မူရင်းအသံကို ခွဲထုတ်သည်။
3. OpenAI Whisper ဖြင့် အချိန်မှတ်သားထားသော transcript လုပ်သည်။
4. OpenAI chat model ဖြင့် segment တစ်ခုချင်းကို သဘာဝကျသော မြန်မာစကားပြေအဖြစ် ဘာသာပြန်သည်။
5. Microsoft Edge TTS ၏ `Nilar` (အမျိုးသမီး) သို့မဟုတ် `Thiha` (အမျိုးသား) Myanmar voice ဖြင့် အသံထုတ်သည်။
6. အသံအချိန်ကို မူရင်း segment များနှင့် ညှိပြီး မူရင်းအသံအားလုံးကို အစားထိုးကာ MP4 အဖြစ် Telegram သို့ ပြန်ပို့သည်။

> **သတိ:** မူရင်း narration အပြင် background music အပါအဝင် မူရင်း audio အားလုံးကို ဖယ်ထုတ်သည်။ Background music ကို ထိန်းထားလိုလျှင် vocal separation module ထပ်ထည့်ရန် လိုသည်။ Lip-sync မဟုတ်ဘဲ speech timing ကို ညှိထားသော AI dubbing ဖြစ်သည်။

## လိုအပ်သည်များ

- Docker နှင့် Docker Compose (အလွယ်ဆုံးနည်းလမ်း)
- Telegram bot token — `@BotFather` တွင် `/newbot` ဖြင့် ဖန်တီးရယူပါ
- OpenAI API key နှင့် billing — transcription/translation အတွက် အသုံးပြုသည်
- Internet connection — Telegram, YouTube, OpenAI နှင့် Edge TTS သို့ ချိတ်ဆက်ရန် လိုသည်

## Docker ဖြင့် စတင်ရန်

```bash
cp .env.example .env
```

`.env` ထဲတွင် အနည်းဆုံး အောက်ပါတန်ဖိုးများကို ဖြည့်ပါ။

```dotenv
TELEGRAM_BOT_TOKEN=your_botfather_token
OPENAI_API_KEY=your_openai_api_key
```

ပြီးလျှင်—

```bash
docker compose up -d --build
docker compose logs -f bot
```

Token များ၊ API key များကို Git သို့ မထည့်ပါနှင့်။ `.env` ကို `.gitignore` တွင် ကြိုတင်ပိတ်ထားပြီးဖြစ်သည်။

## Bot အသုံးပြုနည်း

Telegram တွင် bot ၏ private chat သို့ သွားပြီး—

- `/start` — အသုံးပြုနည်းစတင်ကြည့်ရန်
- `/voice female` — Nilar အမျိုးသမီးအသံ ရွေးရန်
- `/voice male` — Thiha အမျိုးသားအသံ ရွေးရန်
- YouTube Shorts / watch link တစ်ခုလုံးကို ပို့ပါ၊ ဥပမာ `https://youtube.com/shorts/VIDEO_ID`
- သို့မဟုတ် MP4, MOV, MKV, WebM video ကို Telegram တွင် တင်ပို့ပါ

Bot သည် queue အမှတ်စဉ်၊ download/transcription/translation/TTS/upload အခြေအနေများကို message တစ်ခုတည်းတွင် ပြပြီး၊ ပြီးဆုံးလျှင် dubbed video ကို ပြန်ပို့သည်။ တစ်ယောက်လျှင် တစ်ခါတည်း job တစ်ခုသာ လုပ်ဆောင်နိုင်သည်။

## Configuration

| Variable | Default | ရှင်းလင်းချက် |
|---|---:|---|
| `TELEGRAM_BOT_TOKEN` | — | BotFather token (လိုအပ်သည်) |
| `OPENAI_API_KEY` | — | OpenAI API key (လိုအပ်သည်) |
| `OPENAI_BASE_URL` | OpenAI | OpenAI-compatible endpoint လိုလျှင် သုံးနိုင်သည် |
| `WHISPER_MODEL` | `whisper-1` | Speech-to-text model |
| `TRANSLATION_MODEL` | `gpt-4o-mini` | JSON mode ပါသော translation model |
| `DEFAULT_VOICE` | `my-MM-NilarNeural` | Default Myanmar voice |
| `TTS_RATE` | `+0%` | Edge TTS အသံအရှိန်၊ ဥပမာ `+5%` |
| `MAX_VIDEO_SECONDS` | `180` | တစ်ခုလျှင် အများဆုံး video ကြာချိန် |
| `MAX_DOWNLOAD_MB` | `100` | Source file အရွယ်အစား ကန့်သတ်ချက် |
| `MAX_OUTPUT_MB` | `49` | Telegram upload အတွက် output ကန့်သတ်ချက် |
| `MAX_QUEUE_SIZE` | `20` | စောင့်ဆိုင်းနိုင်သော job အရေအတွက် |
| `WORKERS` | `1` | တစ်ပြိုင်နက် processing worker အရေအတွက် |
| `WORK_DIR` | `/tmp/myanmar-dubber` | ယာယီ processing directory |
| `FFMPEG_TIMEOUT_SECONDS` | `900` | ffmpeg/ffprobe timeout |
| `ALLOWED_USER_IDS` | empty | Comma-separated Telegram numeric user IDs; empty ဆိုလျှင် public |
| `YTDLP_COOKIES_FILE` | empty | YouTube cookies ဖိုင်လမ်းကြောင်း (optional) |
| `LOG_LEVEL` | `INFO` | Logging level |

Public bot အဖြစ် ဖွင့်ထားလျှင် သင့်ပေးဆပ်ရသော OpenAI API ကုန်ကျစရိတ် တိုးနိုင်သောကြောင့် `ALLOWED_USER_IDS` ဖြင့် အသုံးပြုခွင့်ကို ကန့်သတ်ထားခြင်း ပိုလုံခြုံသည်။ Job တစ်ခုပြီးတိုင်း source/audio/output ယာယီဖိုင်များကို အလိုအလျောက် ဖျက်သည်။

YouTube hosting IP တွင် download ပိတ်ခံလျှင် video ကို Telegram upload အနေနဲ့ လက်ခံနိုင်သည်။ လိုအပ်သောအခါ Netscape format cookies file ကို server သို့ secure အနေဖြင့် mount ပြီး `YTDLP_COOKIES_FILE` သတ်မှတ်နိုင်သည်။ Cookies ဖိုင်ကို Git တွင် မသိမ်းပါနှင့်။

## Local development

Python 3.11+ နှင့် FFmpeg (`ffmpeg`, `ffprobe`) လိုအပ်သည်။

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
# .env တွင် token များ ဖြည့်ပြီးနောက်
python -m myanmar_dubber
```

Automated checks:

```bash
pytest
ruff check .
```

## ကန့်သတ်ချက်များနှင့် တာဝန်

- AI transcription/translation/dubbing တွင် အမှားအယွင်း ရှိနိုင်သဖြင့် အရေးကြီးသည့်အကြောင်းအရာများကို လူက ပြန်စစ်ဆေးသင့်သည်။
- Whisper, translation API နှင့် Edge TTS အတွက် external services ကို အသုံးပြုထားသောကြောင့် network/provider အပြောင်းအလဲက သက်ရောက်နိုင်သည်။ OpenAI usage ကို provider စျေးနှုန်းအတိုင်း ပေးဆပ်ရသည်။
- Telegram Bot API ၏ file size ကန့်သတ်ချက်ကြောင့် output ကို လိုအပ်လျှင် ပြန်ချုံ့သည်။ ပိုရှည်သော/ကြီးသော video များကို default configuration တွင် ငြင်းဆန်နိုင်သည်။
- YouTube download ပြုလုပ်ရာတွင် YouTube ၏ Terms of Service နှင့် ဒေသဆိုင်ရာဥပဒေများကို လိုက်နာပါ။ ခွင့်ပြုချက်မရှိသော copyright content ကို မန်မျှဝေရန်/ပြန်လည်အသုံးပြုရန် ဤ code က ခွင့်ပြုချက် မပေးပါ။
