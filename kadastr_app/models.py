from django.db import models


class ExcelUpload(models.Model):
    """Admin tomonidan yuklangan Excel fayllar - To'lov ma'lumotlari"""
    fayl = models.FileField(upload_to='excel_files/', verbose_name="Excel fayl")
    yuklangan_vaqt = models.DateTimeField(auto_now_add=True, verbose_name="Yuklangan vaqt")
    yozuvlar_soni = models.IntegerField(default=0, verbose_name="Yozuvlar soni")
    izoh = models.CharField(max_length=255, blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name = "Excel fayl (To'lov)"
        verbose_name_plural = "Excel fayllar (To'lov)"
        ordering = ['-yuklangan_vaqt']

    def __str__(self):
        return f"{self.fayl.name} ({self.yuklangan_vaqt.strftime('%d.%m.%Y %H:%M')})"


class KadastrMalumat(models.Model):
    """Kadastr to'lov ma'lumotlari"""
    excel_fayl = models.ForeignKey(
        ExcelUpload, on_delete=models.CASCADE,
        related_name='malumatlar', verbose_name="Manba fayl"
    )
    viloyat = models.CharField(max_length=200, verbose_name="Viloyat")
    tuman = models.CharField(max_length=200, verbose_name="Tuman")
    mfy = models.CharField(max_length=200, verbose_name="Mahalla nomi")
    kocha = models.CharField(max_length=200, verbose_name="Ko'cha nomi")
    kadastr_raqami = models.CharField(max_length=200, verbose_name="Kadastr raqami", db_index=True)
    invoys_raqami = models.CharField(max_length=200, verbose_name="Invoys raqami", blank=True)
    summa_miqdori = models.CharField(max_length=200, verbose_name="To'lov miqdori", blank=True)
    tolovchi_fio = models.CharField(max_length=300, verbose_name="To'lovchi F.I.O", blank=True)
    tolov_holati = models.CharField(max_length=100, verbose_name="To'lov holati", blank=True)

    class Meta:
        verbose_name = "Kadastr to'lov ma'lumot"
        verbose_name_plural = "Kadastr to'lov ma'lumotlar"

    def __str__(self):
        return f"{self.kadastr_raqami} - {self.tolovchi_fio}"


# ─── Obyekt holati uchun alohida model ────────────────────────────────────────

class ObyektExcelUpload(models.Model):
    """Admin tomonidan yuklangan Excel fayllar - Obyekt holati"""
    fayl = models.FileField(upload_to='obyekt_excel/', verbose_name="Excel fayl")
    yuklangan_vaqt = models.DateTimeField(auto_now_add=True, verbose_name="Yuklangan vaqt")
    yozuvlar_soni = models.IntegerField(default=0, verbose_name="Yozuvlar soni")
    izoh = models.CharField(max_length=255, blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name = "Excel fayl (Obyekt holati)"
        verbose_name_plural = "Excel fayllar (Obyekt holati)"
        ordering = ['-yuklangan_vaqt']

    def __str__(self):
        return f"{self.fayl.name} ({self.yuklangan_vaqt.strftime('%d.%m.%Y %H:%M')})"


class ObyektMalumat(models.Model):
    """Obyekt holati ma'lumotlari"""
    excel_fayl = models.ForeignKey(
        ObyektExcelUpload, on_delete=models.CASCADE,
        related_name='malumatlar', verbose_name="Manba fayl"
    )
    kadastr_raqami = models.CharField(max_length=200, verbose_name="Kadastr raqami", db_index=True)
    viloyat = models.CharField(max_length=200, verbose_name="Viloyat nomi", blank=True)
    tuman = models.CharField(max_length=200, verbose_name="Tuman nomi", blank=True)
    mfy = models.CharField(max_length=200, verbose_name="MFY", blank=True)
    holati = models.CharField(max_length=200, verbose_name="Holati", blank=True)

    class Meta:
        verbose_name = "Obyekt holati"
        verbose_name_plural = "Obyekt holatlari"

    def __str__(self):
        return f"{self.kadastr_raqami} - {self.holati}"


class BotFoydalanuvchi(models.Model):
    """Telegram bot foydalanuvchilari statistikasi"""
    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    ism = models.CharField(max_length=200, blank=True, verbose_name="Ism")
    username = models.CharField(max_length=100, blank=True, verbose_name="Username")
    so_rovlar_soni = models.IntegerField(default=0, verbose_name="So'rovlar soni")
    birinchi_murojaat = models.DateTimeField(auto_now_add=True, verbose_name="Birinchi murojaat")
    oxirgi_murojaat = models.DateTimeField(auto_now=True, verbose_name="Oxirgi murojaat")

    class Meta:
        verbose_name = "Bot foydalanuvchi"
        verbose_name_plural = "Bot foydalanuvchilar"
        ordering = ['-oxirgi_murojaat']

    def __str__(self):
        return f"{self.ism} ({self.telegram_id})"