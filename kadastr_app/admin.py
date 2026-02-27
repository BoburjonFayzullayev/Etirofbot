from django.contrib import admin
from django.utils.html import format_html
from .models import ExcelUpload, KadastrMalumat, BotFoydalanuvchi, ObyektExcelUpload, ObyektMalumat
from .excel_utils import excel_faylni_o_qi, obyekt_excel_o_qi


@admin.register(ExcelUpload)
class ExcelUploadAdmin(admin.ModelAdmin):
    list_display = ['fayl', 'yuklangan_vaqt', 'yozuvlar_soni', 'izoh']
    readonly_fields = ['yuklangan_vaqt', 'yozuvlar_soni']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            if change:
                KadastrMalumat.objects.filter(excel_fayl=obj).delete()
            soni = excel_faylni_o_qi(obj)
            obj.yozuvlar_soni = soni
            obj.save()
            self.message_user(request, f"✅ Excel fayl yuklandi! {soni} ta yozuv saqlandi.")
        except Exception as e:
            self.message_user(request, f"❌ Xatolik: {str(e)}", level='ERROR')


@admin.register(KadastrMalumat)
class KadastrMalumatAdmin(admin.ModelAdmin):
    list_display = ['kadastr_raqami', 'viloyat', 'tuman', 'mfy', 'tolovchi_fio', 'summa_miqdori', 'tolov_holati_badge']
    list_filter = ['viloyat', 'tuman', 'mfy', 'tolov_holati']
    search_fields = ['kadastr_raqami', 'tolovchi_fio', 'invoys_raqami']
    readonly_fields = ['excel_fayl']

    def tolov_holati_badge(self, obj):
        if obj.tolov_holati and "to'lanmagan" in obj.tolov_holati.lower():
            color, icon = '#dc3545', '❌'
        elif obj.tolov_holati and "to'langan" in obj.tolov_holati.lower():
            color, icon = '#28a745', '✅'
        else:
            color, icon = '#6c757d', '⏳'
        return format_html('<span style="color:{}; font-weight:bold;">{} {}</span>', color, icon, obj.tolov_holati)
    tolov_holati_badge.short_description = "To'lov holati"


# ─── Obyekt holati admin ──────────────────────────────────────────────────────

@admin.register(ObyektExcelUpload)
class ObyektExcelUploadAdmin(admin.ModelAdmin):
    list_display = ['fayl', 'yuklangan_vaqt', 'yozuvlar_soni', 'izoh']
    readonly_fields = ['yuklangan_vaqt', 'yozuvlar_soni']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            if change:
                ObyektMalumat.objects.filter(excel_fayl=obj).delete()
            soni = obyekt_excel_o_qi(obj)
            obj.yozuvlar_soni = soni
            obj.save()
            self.message_user(request, f"✅ Obyekt Excel fayl yuklandi! {soni} ta yozuv saqlandi.")
        except Exception as e:
            self.message_user(request, f"❌ Xatolik: {str(e)}", level='ERROR')


@admin.register(ObyektMalumat)
class ObyektMalumatAdmin(admin.ModelAdmin):
    list_display = ['kadastr_raqami', 'viloyat', 'tuman', 'mfy', 'holati_badge']
    list_filter = ['viloyat', 'tuman', 'holati']
    search_fields = ['kadastr_raqami', 'mfy']
    readonly_fields = ['excel_fayl']

    def holati_badge(self, obj):
        holat = obj.holati.lower() if obj.holati else ''
        if 'muhokama' in holat:
            color, icon = '#fd7e14', '🔄'
        elif 'rad' in holat or 'bekor' in holat:
            color, icon = '#dc3545', '❌'
        elif 'tasdiqlangan' in holat or 'qabul' in holat:
            color, icon = '#28a745', '✅'
        else:
            color, icon = '#6c757d', '📋'
        return format_html('<span style="color:{}; font-weight:bold;">{} {}</span>', color, icon, obj.holati)
    holati_badge.short_description = "Holati"


@admin.register(BotFoydalanuvchi)
class BotFoydalanuvchiAdmin(admin.ModelAdmin):
    list_display = ['telegram_id', 'ism', 'username', 'so_rovlar_soni', 'oxirgi_murojaat']
    readonly_fields = ['telegram_id', 'ism', 'username', 'so_rovlar_soni', 'birinchi_murojaat', 'oxirgi_murojaat']
    search_fields = ['telegram_id', 'ism', 'username']
    ordering = ['-so_rovlar_soni']


admin.site.site_header = "🏛️ Kadastr Bot - Admin Panel"
admin.site.site_title = "Kadastr Bot"
admin.site.index_title = "Boshqaruv paneli"