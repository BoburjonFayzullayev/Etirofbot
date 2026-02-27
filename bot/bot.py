#!/usr/bin/env python
"""
Kadastr Telegram Bot
Ishga tushurish: python bot/bot.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kadastr_bot.settings')
django.setup()

import logging
from asgiref.sync import sync_to_async
from django.conf import settings
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)

from kadastr_app.models import KadastrMalumat, BotFoydalanuvchi, ObyektMalumat

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ConversationHandler holatlari
OBYEKT_KADASTR_KIRISH = 1

# ─── Tugma matnlari (bir joyda boshqarish uchun) ─────────────────────────────

BTN_OBYEKT_HOLATI = '🏠 Obyekt holatini tekshirish'
BTN_TOLOV_JARAYON = "📋 To'lov jarayonidagi obyektlar"
BTN_BOT_HAQIDA = 'ℹ️ Bot haqida'
BTN_XATLOV = '📄 Xatlov reja grafigi'
BTN_XULOSA = "🔎 Xulosalarni ko'rish"
BTN_HUQUQIY_ASOSLAR = '📖 Huquqiy asoslar'
BTN_HUQUQIY_AI = '🎥 Videorolik'
BTN_QOLLANMA = "🧑‍🏫 Qo'llanma va savol-javoblar"
BTN_BEKOR = '❌ Bekor qilish'

ASOSIY_KLAVIATURA = ReplyKeyboardMarkup(
    [
        [BTN_OBYEKT_HOLATI],
        [BTN_TOLOV_JARAYON],
        [BTN_BOT_HAQIDA, BTN_XATLOV],
        [BTN_XULOSA],
        [BTN_HUQUQIY_ASOSLAR],
        [BTN_HUQUQIY_AI],
        [BTN_QOLLANMA],
    ],
    resize_keyboard=True
)

BEKOR_TUGMA = ReplyKeyboardMarkup(
    [[BTN_BEKOR]],
    resize_keyboard=True
)

# Boshqa tugmalar ro'yxati (ConversationHandler ichida tekshirish uchun)
BOSHQA_TUGMALAR = [
    BTN_OBYEKT_HOLATI, BTN_TOLOV_JARAYON,
    BTN_BOT_HAQIDA, BTN_XATLOV, BTN_XULOSA, BTN_HUQUQIY_ASOSLAR,
    BTN_HUQUQIY_AI, BTN_QOLLANMA,
]


# ─── Yordamchi funksiyalar ────────────────────────────────────────────────────

def fio_yashir(fio: str) -> str:
    if not fio:
        return '—'
    natija = []
    for soz in fio.split():
        if len(soz) <= 2:
            natija.append(soz)
        else:
            natija.append(soz[:2] + '●' * (len(soz) - 2))
    return ' '.join(natija)


# ─── Sync Django ORM funksiyalari ─────────────────────────────────────────────

def _foydalanuvchi_saqlash(user_id, ism, username):
    obj, yaratildi = BotFoydalanuvchi.objects.get_or_create(
        telegram_id=user_id,
        defaults={'ism': ism, 'username': username}
    )
    if not yaratildi:
        obj.so_rovlar_soni += 1
        obj.save()


def _statistika_yangilash(user_id, ism, username):
    try:
        f = BotFoydalanuvchi.objects.get(telegram_id=user_id)
        f.so_rovlar_soni += 1
        f.save()
    except BotFoydalanuvchi.DoesNotExist:
        BotFoydalanuvchi.objects.create(
            telegram_id=user_id, ism=ism,
            username=username, so_rovlar_soni=1
        )


def _qidirish(kadastr_raqam):
    qs = KadastrMalumat.objects.filter(kadastr_raqami__icontains=kadastr_raqam)
    return list(qs.values(
        'viloyat', 'tuman', 'mfy', 'kocha', 'kadastr_raqami',
        'invoys_raqami', 'summa_miqdori', 'tolovchi_fio', 'tolov_holati'
    ))


def _toshkent_tumanlar():
    tumanlar = (
        KadastrMalumat.objects
        .filter(viloyat__icontains='toshkent')
        .values_list('tuman', flat=True)
        .distinct()
        .order_by('tuman')
    )
    return list(tumanlar)


def _tuman_fuqarolari(tuman_nomi):
    qs = KadastrMalumat.objects.filter(
        viloyat__icontains='toshkent',
        tuman__iexact=tuman_nomi,
        tolov_holati__icontains="to'lanmagan"
    ).values(
        'kadastr_raqami', 'mfy', 'kocha', 'invoys_raqami', 'tolovchi_fio', 'summa_miqdori', 'tolov_holati'
    ).order_by('tolovchi_fio')
    return list(qs)


def _obyekt_qidirish(kadastr_raqam):
    qs = ObyektMalumat.objects.filter(kadastr_raqami__icontains=kadastr_raqam)
    return list(qs.values('kadastr_raqami', 'viloyat', 'tuman', 'mfy', 'holati'))


# Async wrapperlar
foydalanuvchi_saqlash = sync_to_async(_foydalanuvchi_saqlash)
statistika_yangilash = sync_to_async(_statistika_yangilash)
qidirish = sync_to_async(_qidirish)
toshkent_tumanlar = sync_to_async(_toshkent_tumanlar)
tuman_fuqarolari = sync_to_async(_tuman_fuqarolari)
obyekt_qidirish = sync_to_async(_obyekt_qidirish)


# ─── Asosiy handlerlar ────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ism = f"{user.first_name or ''} {user.last_name or ''}".strip()
    await foydalanuvchi_saqlash(user.id, ism, user.username or '')
    xabar = (
        f"🏛️ E'tirof Tosh Vil.botiga xush kelibsiz!\n\n"
        f"👤 Salom, *{user.first_name}*!\n\n"
        f"📋 Bu bot orqali E'tirof tizimidagi jarayonlarni bilib "
        f"olishingiz mumkin.\n\n"
        f"Quyidagi tugmalardan birini tanlang:"
    )
    await update.message.reply_text(xabar, parse_mode='Markdown', reply_markup=ASOSIY_KLAVIATURA)


async def yordam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    xabar = (
        "ℹ️ *Bot haqida*\n\n"
        "Bu bot orqali E'tirof tizimidagi jarayonlar haqida ma'lumotga ega bo'lishingiz mumkin.\n\n"
        "Huquqiy yangiliklarni kuzatib borish uchun\n"
        "T.me/toshviladliya kanaliga kirishingiz mumkin.\n\n"
        "Kadastr sohasidagi yangiliklarni kuzatib borish uchun "
        "t.me/tvkad kanaliga kirishingiz mumkin.\n\n"
        "📌 *Qanday ishlatish:*\n"
        "1. Kadastr raqamingizni yuboring.\n"
        "2. Bot ma'lumotlarni ko'rsatadi.\n\n"
        "📌 *Kadastr raqam namunasi:*\n"
        "`11:13:42:02:01:0406`\n\n"
        "❓ Muammo yuzaga kelsa admin bilan bog'laning."
    )
    await update.message.reply_text(xabar, parse_mode='Markdown', reply_markup=ASOSIY_KLAVIATURA)


async def xatlov(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Saytni ochish 🔗", url="https://etirof.kadastr.uz/plan-grafic")]]
    await update.message.reply_text(
        "🌐 Xatlov bo'yicha ma'lumot olish uchun saytga o'ting:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def huquq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Videorolikni ko'rish 🔗", url="https://www.youtube.com/watch?v=nNx6vaK0F-w")]]
    await update.message.reply_text(
        "Videorolikni ko'rish uchun pastdagi tugmani bosing",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def qollanma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Saytni ochish 🔗", url="https://etirof.kadastr.uz/helps")]]
    await update.message.reply_text(
        "Kadastrga oid savollar va javoblar:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def xulosa_kurish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Saytni ochish 🔗", url="https://etirof.kadastr.uz/open-map")]]
    await update.message.reply_text(
        "E'tirof bo'yicha xulosalarni ko'rish uchun saytga kiring",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def huquq_kodeks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Saytni ochish 🔗", url="https://kadastr.uz/uz/qonun-kodeks")]]
    await update.message.reply_text(
        "E'tirof bo'yicha huquqiy asoslarni ko'rish uchun saytga kiring",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── Obyekt holati ConversationHandler ───────────────────────────────────────

async def obyekt_holati_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi 'Obyekt holatini tekshirish' tugmasini bosdi"""
    await update.message.reply_text(
        "🏠 *Obyekt holati*\n\n"
        "📋 Kadastr raqamini kiriting:\n\n"
        "📌 *Namuna:* `11:12:41:02:01:0254`\n\n"
        "Bekor qilish uchun tugmani bosing.",
        parse_mode='Markdown',
        reply_markup=BEKOR_TUGMA
    )
    return OBYEKT_KADASTR_KIRISH


async def obyekt_kadastr_qidirish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi kadastr raqamini kiritdi — qidiruv"""
    kiritilgan = update.message.text.strip()

    # Bekor qilish
    if kiritilgan == BTN_BEKOR:
        await update.message.reply_text(
            "✅ Bekor qilindi.",
            reply_markup=ASOSIY_KLAVIATURA
        )
        return ConversationHandler.END

    # Agar foydalanuvchi boshqa asosiy tugmalarni bossa — suhbatdan chiqish
    if kiritilgan in BOSHQA_TUGMALAR:
        await update.message.reply_text(
            "✅ Obyekt qidiruvdan chiqildi.",
            reply_markup=ASOSIY_KLAVIATURA
        )
        return ConversationHandler.END

    await update.message.reply_chat_action('typing')
    natijalar = await obyekt_qidirish(kiritilgan)

    if not natijalar:
        await update.message.reply_text(
            f"❌ *Ma'lumot topilmadi!*\n\n"
            f"🔎 Qidirilgan raqam: `{kiritilgan}`\n\n"
            f"📌 Kadastr raqamni to'g'ri kiriting yoki boshqa raqam kiriting:\n"
            f"Namuna: `11:12:41:02:01:0254`\n\n"
            f"Bekor qilish uchun tugmani bosing.",
            parse_mode='Markdown',
            reply_markup=BEKOR_TUGMA
        )
        return OBYEKT_KADASTR_KIRISH

    # Natijalar topildi
    xabar = f"✅ *{len(natijalar)} ta natija topildi*\n\n" if len(natijalar) > 1 else ""

    for m in natijalar:
        holat = m['holati'] or '—'
        holat_lower = holat.lower()
        if 'muhokama' in holat_lower:
            holat_emoji = "🔄"
        elif 'rad' in holat_lower or 'bekor' in holat_lower:
            holat_emoji = "❌"
        elif 'tasdiqlangan' in holat_lower or 'qabul' in holat_lower:
            holat_emoji = "✅"
        else:
            holat_emoji = "📋"

        xabar += (
            f"🏠 *Obyekt ma'lumotlari*\n"
            f"{'─' * 30}\n"
            f"📋 *Kadastr raqami:* `{m['kadastr_raqami']}`\n"
            f"🗺️ *Viloyat:* {m['viloyat'] or '—'}\n"
            f"🏘️ *Tuman:* {m['tuman'] or '—'}\n"
            f"🏡 *MFY:* {m['mfy'] or '—'}\n"
            f"{holat_emoji} *Holati:* {holat}\n"
            f"{'─' * 30}\n\n"
        )

    xabar += "🔍 Boshqa kadastr raqam kiriting yoki bekor qiling."

    await update.message.reply_text(
        xabar,
        parse_mode='Markdown',
        reply_markup=BEKOR_TUGMA
    )
    return OBYEKT_KADASTR_KIRISH


async def obyekt_bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bekor qilindi.", reply_markup=ASOSIY_KLAVIATURA)
    return ConversationHandler.END


# ─── E'tiroflar (tumanlar) ────────────────────────────────────────────────────

async def etiroflar_tumanlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_chat_action('typing')
    tumanlar = await toshkent_tumanlar()

    if not tumanlar:
        await update.message.reply_text(
            "⚠️ Hozircha Toshkent viloyati bo'yicha ma'lumot mavjud emas.",
            reply_markup=ASOSIY_KLAVIATURA
        )
        return

    keyboard = []
    qator = []
    for tuman in tumanlar:
        qator.append(InlineKeyboardButton(f"🏘️ {tuman}", callback_data=f"tuman:{tuman}"))
        if len(qator) == 2:
            keyboard.append(qator)
            qator = []
    if qator:
        keyboard.append(qator)

    await update.message.reply_text(
        f"📋 *To'lov jarayonidagi obyektlar*\n"
        f"🗺️ *Toshkent viloyati*\n\n"
        f"Quyidagi tumanlardan birini tanlang:\n"
        f"_(Jami {len(tumanlar)} ta tuman)_",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def tuman_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    raw = query.data[len("tuman:"):]

    if "|" in raw:
        tuman_nomi, sahifa_str = raw.rsplit("|", 1)
        sahifa = int(sahifa_str)
    else:
        tuman_nomi = raw
        sahifa = 0

    SAHIFA_HAJMI = 15
    fuqarolar = await tuman_fuqarolari(tuman_nomi)

    if not fuqarolar:
        keyboard = [[InlineKeyboardButton("◀️ Tumanlar ro'yxatiga qaytish", callback_data="tumanlar_royxat")]]
        await query.edit_message_text(
            f"✅ *{tuman_nomi}*\n\nBu tumanda to'lov jarayonidagi fuqarolar topilmadi.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    jami = len(fuqarolar)
    jami_sahifa = (jami + SAHIFA_HAJMI - 1) // SAHIFA_HAJMI
    sahifa = max(0, min(sahifa, jami_sahifa - 1))

    boshlash = sahifa * SAHIFA_HAJMI
    sahifa_fuqarolar = fuqarolar[boshlash:boshlash + SAHIFA_HAJMI]

    xabar = (
        f"📋 *To'lov jarayonidagi obyektlar*\n"
        f"🏘️ *{tuman_nomi}*\n"
        f"{'─' * 28}\n"
        f"Jami: *{jami} ta* fuqaro | Sahifa: *{sahifa + 1}/{jami_sahifa}*\n"
        f"{'─' * 28}\n\n"
    )

    for i, f in enumerate(sahifa_fuqarolar, boshlash + 1):
        summa = f['summa_miqdori'] or '—'
        xabar += (
            f"*{i}.* 👤 {fio_yashir(f['tolovchi_fio'])}\n"
            f"   📋 `{f['kadastr_raqami']}`\n"
            f"🧾 *Invoys raqami:* {f['invoys_raqami']}\n"
            f"🏘️ {f['mfy']}\n"
            f"🏘️  {f['kocha']}\n"
            f"   💰 {summa} so'm\n"
            f"   ❌ {f['tolov_holati']}\n\n"
        )

    nav_buttons = []
    if sahifa > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"tuman:{tuman_nomi}|{sahifa - 1}"))
    if sahifa + 1 < jami_sahifa:
        nav_buttons.append(InlineKeyboardButton("Keyingi ▶️", callback_data=f"tuman:{tuman_nomi}|{sahifa + 1}"))

    keyboard = []
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("◀️ Tumanlar ro'yxatiga qaytish", callback_data="tumanlar_royxat")])

    await query.edit_message_text(
        xabar,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def tumanlar_royxat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tumanlar = await toshkent_tumanlar()
    keyboard = []
    qator = []
    for tuman in tumanlar:
        qator.append(InlineKeyboardButton(f"🏘️ {tuman}", callback_data=f"tuman:{tuman}"))
        if len(qator) == 2:
            keyboard.append(qator)
            qator = []
    if qator:
        keyboard.append(qator)

    await query.edit_message_text(
        f"📋 *To'lov jarayonidagi obyektlar*\n"
        f"🗺️ *Toshkent viloyati*\n\n"
        f"Quyidagi tumanlardan birini tanlang:\n"
        f"_(Jami {len(tumanlar)} ta tuman)_",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── Kadastr to'lov qidirish ──────────────────────────────────────────────────

async def kadastr_qidirish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kiritilgan = update.message.text.strip()


    if kiritilgan == BTN_BOT_HAQIDA:
        await yordam(update, context)
        return

    if kiritilgan == BTN_XATLOV:
        await xatlov(update, context)
        return

    if kiritilgan == BTN_HUQUQIY_AI:
        await huquq(update, context)
        return

    if kiritilgan == BTN_TOLOV_JARAYON:
        await etiroflar_tumanlar(update, context)
        return

    if kiritilgan == BTN_QOLLANMA:
        await qollanma(update, context)
        return

    if kiritilgan == BTN_XULOSA:
        await xulosa_kurish(update, context)
        return

    if kiritilgan == BTN_HUQUQIY_ASOSLAR:
        await huquq_kodeks(update, context)
        return

    # Agar hech qaysi tugma bo'lmasa — kadastr raqam sifatida qidirish
    ism = f"{user.first_name or ''} {user.last_name or ''}".strip()
    await statistika_yangilash(user.id, ism, user.username or '')
    await update.message.reply_chat_action('typing')

    natijalar = await qidirish(kiritilgan)

    if not natijalar:
        await update.message.reply_text(
            f"❌ *Ma'lumot topilmadi!*\n\n"
            f"🔎 Qidirilgan raqam: `{kiritilgan}`\n\n"
            f"📌 Iltimos, kadastr raqamni to'g'ri kiriting.\n"
            f"Namuna: `11:13:42:02:01:0406`",
            parse_mode='Markdown',
            reply_markup=ASOSIY_KLAVIATURA
        )
        return

    if len(natijalar) > 1:
        xabar = f"🔍 `{kiritilgan}` bo'yicha *{len(natijalar)} ta natija* topildi:\n\n"
        for i, m in enumerate(natijalar[:5], 1):
            xabar += f"{i}. `{m['kadastr_raqami']}` — {fio_yashir(m['tolovchi_fio'])}\n"
        if len(natijalar) > 5:
            xabar += f"\n... va yana {len(natijalar) - 5} ta\n"
        xabar += "\n📌 Aniqroq raqam kiriting."
        await update.message.reply_text(xabar, parse_mode='Markdown', reply_markup=ASOSIY_KLAVIATURA)
        return

    m = natijalar[0]
    holat = m['tolov_holati'] or ''
    if "to'lanmagan" in holat.lower():
        holat_emoji = "❌"
    elif "to'langan" in holat.lower():
        holat_emoji = "✅"
    else:
        holat_emoji = "⏳"

    xabar = (
        f"✅ *Ma'lumot topildi!*\n"
        f"{'─' * 30}\n"
        f"🗺️ *Viloyat:* {m['viloyat']}\n"
        f"🏘️ *Tuman:* {m['tuman']}\n"
        f"🏘️ *Mahalla:* {m['mfy']}\n"
        f"🏘️ *Ko'cha nomi:* {m['kocha']}\n"
        f"📋 *Kadastr raqami:* `{m['kadastr_raqami']}`\n"
        f"🧾 *Invoys raqami:* `{m['invoys_raqami']}`\n"
        f"💰 *To'lov miqdori:* `{m['summa_miqdori']}` so'm\n"
        f"👤 *To'lovchi F.I.O:* {fio_yashir(m['tolovchi_fio'])}\n"
        f"{holat_emoji} *To'lov holati:* {holat}\n"
        f"{'─' * 30}"
    )
    await update.message.reply_text(xabar, parse_mode='Markdown', reply_markup=ASOSIY_KLAVIATURA)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        print("❌ XATO: TELEGRAM_BOT_TOKEN o'rnatilmagan!")
        sys.exit(1)

    print("🤖 Kadastr Bot ishga tushmoqda...")
    app = Application.builder().token(token).build()

    # Obyekt holati ConversationHandler
    obyekt_conv = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(f"^{BTN_OBYEKT_HOLATI}$"),
                obyekt_holati_start
            )
        ],
        states={
            OBYEKT_KADASTR_KIRISH: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    obyekt_kadastr_qidirish
                )
            ],
        },
        fallbacks=[
            CommandHandler("bekor", obyekt_bekor),
            MessageHandler(
                filters.Regex(f"^{BTN_BEKOR}$"),
                obyekt_bekor
            ),
        ],
        allow_reentry=True,
    )

    # Command handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", yordam))
    app.add_handler(CommandHandler("huquq", huquq))
    app.add_handler(CommandHandler("xatlov", xatlov))
    app.add_handler(CommandHandler("qollanma", qollanma))
    app.add_handler(CommandHandler("xulosa_kurish", xulosa_kurish))
    app.add_handler(CommandHandler("huquq_kodeks", huquq_kodeks))
    app.add_handler(CommandHandler("etiroflar", etiroflar_tumanlar))

    # ConversationHandler eng avval qo'shilishi kerak
    app.add_handler(obyekt_conv)

    # Inline callback handlerlar
    app.add_handler(CallbackQueryHandler(tumanlar_royxat_callback, pattern="^tumanlar_royxat$"))
    app.add_handler(CallbackQueryHandler(tuman_callback, pattern="^tuman:"))

    # Umumiy text handler (kadastr qidirish va tugma yo'naltirish)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kadastr_qidirish))

    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()