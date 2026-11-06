# Myanmar Video Dubbing Telegram Bot

YouTube Shorts / YouTube link သို့မဟုတ် Telegram video upload ကို လက်ခံပြီး မူရင်းအသံအားလုံးကို ဖယ်ကာ **မြန်မာလို AI dubbing ပါသော MP4** ပြန်ပေးသော bot ဖြစ်သည်။ ဤ version တွင် **OpenAI/Gemini မလိုအပ်ဘဲ** free-quota Groq API ကို transcription/translation အတွက် အသုံးပြုထားသည်။

## Features

- Groq `whisper-large-v3-turbo` ဖြင့် timestamped transcription
- Groq chat model ဖြင့် မြန်မာစကားပြေ dubbing script
- Edge TTS `my-MM-ThihaNeural` (ယောက်ျားလေးအသံ — default) သို့မဟုတ် `my-MM-NilarNeural`
- မူရင်း audio အားလုံးကို Myanmar dub အသစ်ဖြင့် အစားထိုးခြင်း
- Lightweight video enhancement: denoise, sharpen, contrast/saturation adjustment
- Queue, progress updates, access control, size limits, temporary-file cleanup
- Local development အတွက် Telegram long polling
- Render Free Web Service အတွက် FastAPI health endpoint + Telegram webhook
- Groq free quota ပြည့်လျှင် paid fallback မလုပ်ဘဲ အသိပေးခြင်း

> Video enhancement သည် AI super-resolution မဟုတ်ဘဲ free/low-CPU FFmpeg filters ဖြစ်သည်။ မူရင်း background music အပါအဝင် မူရင်း audio အားလုံးကို ဖယ်ထုတ်သည်။ Lip-sync မဟုတ်ဘဲ speech timing ကို ညှိထားသည်။

## API keys and links

| Service | Link | Required |
|---|---|---|
| Telegram BotFather | https://t.me/BotFather | `TELEGRAM_BOT_TOKEN` ရရန် |
| Groq API Keys | https://console.groq.com/keys | Free `GROQ_API_KEY` ရရန် |
| Groq plan/billing | https://console.groq.com/settings/billing | Free plan/limits စစ်ရန် |
| Render Dashboard | https://dashboard.render.com/ | Web Service deploy ရန် |

OpenAI key၊ Gemini key၊ paid billing account တို့ မလိုအပ်ပါ။ Free quotas များက unlimited မဟုတ်သဖြင့် provider account တွင် လက်ရှိ limits ကို စစ်ဆေးပါ။

## Render Free Web Service deployment

**Background Worker မရွေးပါနှင့်။** New → **Web Service** → **Free** compute plan ကို ရွေးပါ။

### 1. Repository settings

| Setting | Value |
|---|---|
| Repository | `physho158-cell/money` |
| Branch | `main` (ဤ changes များ merge ပြီးနောက်) |
| Language / Runtime | `Docker` |
| Root Directory | blank |
| Dockerfile Path | `./Dockerfile` |
| Compute plan | **Free** |
| Health Check Path | `/health` |
| Instance Count | `1` |

Docker command ကို blank ထားပါ။ Dockerfile ၏ `CMD ["python", "-m", "myanmar_dubber"]` ကို အသုံးပြုပါမည်။ `docker-compose.yml` ကို Render တွင် အသုံးပြုရန် မလိုပါ။

### 2. Environment variables

```dotenv
TELEGRAM_BOT_TOKEN=your_botfather_token
GROQ_API_KEY=your_groq_free_api_key
APP_MODE=webhook
WEBHOOK_URL=https://your-service.onrender.com
GROQ_WHISPER_MODEL=whisper-large-v3-turbo
GROQ_TRANSLATION_MODEL=openai/gpt-oss-120b
DEFAULT_VOICE=my-MM-ThihaNeural
TTS_RATE=+0%
VIDEO_ENHANCE=true
MAX_VIDEO_SECONDS=120
MAX_DOWNLOAD_MB=300
MAX_OUTPUT_MB=45
MAX_QUEUE_SIZE=5
WORKERS=1
WORK_DIR=/tmp/myanmar-dubber
FFMPEG_TIMEOUT_SECONDS=900
ALLOWED_USER_IDS=
LOG_LEVEL=INFO
```

- `WEBHOOK_URL` တွင် Render service ၏ အမှတတ瓷牙 URL ကို အသုံးပြုပါ။ `RENDER_EXTERNAL_URL` ရှိလျှင် app က fallback အနေဖြင့် အသုံးပြုနိုင်သည်။
- `PORT` ကို Render က auto ပေးသောကြောင့် မထည့်ပါနှင့်။
- `WEBHOOK_SECRET` မထည့်လည်း app က bot token မှ secret ကို derive လုပ်သည်။ Custom secret လိုလျှင် ထည့်နိုင်သည်။
- Public bot မဖွင့်မီ `ALLOWED_USER_IDS=123456789,987654321` ဖြင့် အသုံးပြုခွင့်ကို ကန့်သတ်ပါ။
- YouTube cookies မလိုသေးလျှင် `YTDLP_COOKIES_FILE` မထည့်ပါနှင့်။

### 3. Deploy and verify

1. **Create Web Service / Deploy** နှိပ်ပါ။
2. Build log တွင် FFmpeg နှင့် Python packages install ဖြစ်သည်ကို စစ်ပါ။
3. Browser တွင် `https://your-service.onrender.com/health` ကို ဖွင့်ပါ။

```json
{"status":"ok","webhook_configured":true,"mode":"webhook"}
```

4. `webhook_configured` မှာ `false` ဖြစ်နေလျှင် `WEBHOOK_URL` ကို service URL အမှန်ဖြင့် ထည့်ပြီး redeploy/restart လုပ်ပါ။
5. Log တွင် `Telegram webhook registered` ပါရပါမည်။

### 4. Telegram test

```text
/start
/voice male
```

ပြီးလျှင် တိုတောင်းသော Shorts link သို့မဟုတ် Telegram video file ကို ပို့ပါ။ `/voice female` ဖြင့် Nilar အသံသို့ ပြောင်းနိုင်သည်။

Render Free Web Service သည် inbound traffic မရှိဘဲ ၁၅ မိနစ်ကြာလျှင် spin down ဖြစ်ပြီး နောက် request ရောက်လာလျှင် ပြန်စတင်ရန် ခန့်စောင့်ရနိုင်သည်။ ပထမ `/start` မဖြေခင် cold start ပြီးအောင် စောင့်ပြီး ပြန်ပို့ကြည့်ပါ။ Deploy/restart/spin down ဖြစ်လျှင် in-memory queue နှင့် လက်ရှိ job များ ပျက်နိုင်သည်။

## Local development

Python 3.11+ နှင့် FFmpeg (`ffmpeg`, `ffprobe`) လိုအပ်သည်။

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
# .env ထဲတွင် TELEGRAM_BOT_TOKEN နှင့် GROQ_API_KEY ဖြည့်ပါ
# Local development အတွက် APP_MODE=polling ထားပါ
python -m myanmar_dubber
```

Docker Compose ဖြင့်လည်း polling mode run နိုင်သည်—

```bash
cp .env.example .env
# .env ဖြည့်ပြီးနောက်
docker compose up -d --build
docker compose logs -f bot
```

Automated checks:

```bash
pytest
ruff check .
```

## Configuration reference

| Variable | Default (code) | Description |
|---|---:|---|
| `GROQ_WHISPER_MODEL` | `whisper-large-v3-turbo` | Groq transcription model |
| `GROQ_TRANSLATION_MODEL` | `openai/gpt-oss-120b` | Groq translation model; Qwen model ဖြင့် ပြောင်းစမ်းနိုင်သည် |
| `DEFAULT_VOICE` | `my-MM-ThihaNeural` | Default Myanmar male voice |
| `VIDEO_ENHANCE` | `true` | Lightweight denoise/sharpen/colour enhancement |
| `APP_MODE` | `polling` | `polling` or `webhook` |
| `WEBHOOK_URL` | `RENDER_EXTERNAL_URL` fallback | Public base URL; no trailing path needed |
| `WEBHOOK_SECRET` | derived from bot token | Telegram webhook header validation |
| `PORT` | `10000` | Web server port; Render sets automatically |
| `MAX_VIDEO_SECONDS` | `180` | Maximum video duration; `.env.example` uses 120 (2 minutes) |
| `MAX_DOWNLOAD_MB` | `300` | Source size limit; `.env.example` also uses 300 |
| `MAX_OUTPUT_MB` | `49` | Telegram output limit; `.env.example` uses 45 |
| `WORKERS` | `1` | Internal processing workers; keep at 1 on free Render |

## Limitations and safety

- Groq free quota နှင့် Edge TTS availability က provider အပြောင်းအလဲအလိုက် သက်ရောက်နိုင်သည်။ Bot သည် quota ပြည့်လျှင် paid plan သို့ auto-switch မလုပ်ပါ။
- Audio/transcript ကို Groq သို့လည်းကောင်း၊ မြန်မာစာသားကို Edge TTS သို့လည်းကောင်း ပေးပို့သည်။ Private/sensitive content မတင်ပါနှင့်။
- YouTube download ပိတ်ခံရလျှင် Telegram upload ကို အသုံးပြုနိုင်သည်။ Cookies လိုအပ်လာလျှင် secure secret file အနေဖြင့် သီးသန့်ပြင်ဆင်ပါ။
- `MAX_DOWNLOAD_MB=300` သည် source ကန့်သတ်ချက်ဖြစ်ပြီး Telegram Bot API ၏ ကိုယ်ပိုင် file limits များကလည်း ဆက်လက်သက်ရောက်သည်။ Output ကို `MAX_OUTPUT_MB` အတိုင်း compress လုပ်သည်။ 300 MB/2-minute videos များကို Free Render တွင် process လုပ်ရာတွင် memory/timeout ပြဿနာ တက်လျှင် limit များကို ပြန်လျှော့ပါ။
- ကိုယ်ပိုင် သို့မဟုတ် ခွင့်ပြုချက်ရထားသော content ကိုသာ အသုံးပြုပါ။ YouTube/TikTok terms နှင့် copyright ကို လိုက်နာပါ။
- **TikTok direct posting သည် ဤ version တွင် မပါဝင်သေးပါ။** Official Content Posting API ၏ `video.publish` approval၊ OAuth နှင့် refresh-token rotation အတွက် persistent secure token storage လိုအပ်သည်။ Unaudited clients ၏ posts များလည်း private-only ဖြစ်နိုင်သည်။
