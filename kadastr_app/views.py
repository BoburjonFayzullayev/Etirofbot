from django.shortcuts import render
from .models import KadastrMalumat, BotFoydalanuvchi, ExcelUpload


def bosh_sahifa(request):
    context = {
        'jami_yozuvlar': KadastrMalumat.objects.count(),
        'jami_foydalanuvchilar': BotFoydalanuvchi.objects.count(),
        'jami_fayllar': ExcelUpload.objects.count(),
    }
    return render(request, 'kadastr_app/bosh_sahifa.html', context)
