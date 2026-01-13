"""
MEB RAG Sistemi - Exam PDF Generator
ReportLab ile sınav PDF'i oluşturur.
"""
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import black, gray, lightgrey, HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, PageBreak, KeepTogether, Flowable
)
import re
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config.settings import get_settings
from .question_selector import SelectedQuestion
from .question_indexer import parse_question_filename

logger = logging.getLogger(__name__)
settings = get_settings()

# Türkçe karakter desteği için font
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc"
]


def register_fonts():
    """Türkçe karakter destekli fontları kaydet."""
    for font_path in FONT_PATHS:
        if os.path.exists(font_path):
            try:
                if "Bold" in font_path:
                    pdfmetrics.registerFont(TTFont("TurkishBold", font_path))
                else:
                    pdfmetrics.registerFont(TTFont("Turkish", font_path))
            except Exception as e:
                logger.warning(f"Font kaydedilemedi: {font_path}, hata: {e}")

    # Fallback olarak Helvetica kullan
    return "Turkish" if "Turkish" in pdfmetrics.getRegisteredFontNames() else "Helvetica"


class ExamPDFGenerator:
    """Sınav PDF'i oluşturucu."""

    # Sayfa boyutları
    PAGE_WIDTH, PAGE_HEIGHT = A4
    MARGIN = 2 * cm

    # Renkler
    PRIMARY_COLOR = HexColor("#1a365d")  # Koyu mavi
    SECONDARY_COLOR = HexColor("#2d3748")  # Koyu gri
    LIGHT_BG = HexColor("#f7fafc")  # Açık gri arka plan

    def __init__(self, output_dir: Optional[str] = None):
        """
        Args:
            output_dir: PDF çıktı dizini
        """
        self.output_dir = Path(output_dir or getattr(settings, "exam_output_dir", "data/generated_exams"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Fontları kaydet
        self.font_name = register_fonts()
        self.bold_font = "TurkishBold" if "TurkishBold" in pdfmetrics.getRegisteredFontNames() else self.font_name

        # Stilleri oluştur
        self._setup_styles()

    def _setup_styles(self):
        """Paragraf stillerini ayarla."""
        self.styles = getSampleStyleSheet()

        # Başlık stili
        self.styles.add(ParagraphStyle(
            name="ExamTitle",
            fontName=self.bold_font,
            fontSize=18,
            textColor=self.PRIMARY_COLOR,
            alignment=TA_CENTER,
            spaceAfter=20
        ))

        # Alt başlık stili
        self.styles.add(ParagraphStyle(
            name="ExamSubtitle",
            fontName=self.font_name,
            fontSize=12,
            textColor=self.SECONDARY_COLOR,
            alignment=TA_CENTER,
            spaceAfter=10
        ))

        # Soru numarası stili
        self.styles.add(ParagraphStyle(
            name="QuestionNumber",
            fontName=self.bold_font,
            fontSize=11,
            textColor=self.PRIMARY_COLOR,
            spaceBefore=15,
            spaceAfter=5
        ))

        # Normal metin stili
        self.styles.add(ParagraphStyle(
            name="ExamText",
            fontName=self.font_name,
            fontSize=10,
            textColor=black,
            alignment=TA_LEFT
        ))

        # Cevap anahtarı stili
        self.styles.add(ParagraphStyle(
            name="AnswerKey",
            fontName=self.font_name,
            fontSize=9,
            textColor=self.SECONDARY_COLOR
        ))

    def _create_cover_page(
        self,
        title: str,
        question_count: int,
        kazanimlar: List[str],
        difficulty_distribution: Dict[str, int]
    ) -> List:
        """
        Kapak sayfası elementlerini oluşturur.

        Returns:
            Platypus element listesi
        """
        elements = []

        # Boşluk
        elements.append(Spacer(1, 3 * cm))

        # Başlık
        elements.append(Paragraph(title, self.styles["ExamTitle"]))
        elements.append(Spacer(1, 1 * cm))

        # Tarih
        date_str = datetime.now().strftime("%d.%m.%Y")
        elements.append(Paragraph(f"Tarih: {date_str}", self.styles["ExamSubtitle"]))
        elements.append(Spacer(1, 2 * cm))

        # Sınav bilgileri tablosu
        info_data = [
            ["Soru Sayısı:", str(question_count)],
            ["Kolay Soru:", str(difficulty_distribution.get("kolay", 0))],
            ["Orta Soru:", str(difficulty_distribution.get("orta", 0))],
            ["Zor Soru:", str(difficulty_distribution.get("zor", 0))],
        ]

        info_table = Table(info_data, colWidths=[6 * cm, 4 * cm])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), self.font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("TEXTCOLOR", (0, 0), (0, -1), self.PRIMARY_COLOR),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 2 * cm))

        # Kazanımlar
        elements.append(Paragraph("Kapsanan Kazanımlar:", self.styles["ExamSubtitle"]))
        elements.append(Spacer(1, 0.5 * cm))

        for kazanim in kazanimlar[:10]:  # Max 10 kazanım göster
            elements.append(Paragraph(f"• {kazanim}", self.styles["ExamText"]))

        if len(kazanimlar) > 10:
            elements.append(Paragraph(f"... ve {len(kazanimlar) - 10} kazanım daha", self.styles["ExamText"]))

        elements.append(Spacer(1, 3 * cm))

        # Ad Soyad alanı
        elements.append(Paragraph("Ad Soyad: _______________________________", self.styles["ExamText"]))
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph("Sınıf: ____________  No: ____________", self.styles["ExamText"]))

        elements.append(PageBreak())

        return elements

    def _create_question_content(
        self,
        question: SelectedQuestion,
        cell_width: float,
        cell_height: float
    ) -> List:
        """
        Tek bir soru için hücre içeriğini liste olarak oluşturur.

        Args:
            question: Soru bilgisi
            cell_width: Hücre genişliği
            cell_height: Hücre yüksekliği

        Returns:
            List of flowables
        """
        elements = []

        # Soru numarası ve zorluk (metin bazlı)
        difficulty_label = {
            "kolay": "[Kolay]",
            "orta": "[Orta]",
            "zor": "[Zor]"
        }.get(question.difficulty, "")
        header = f"<b>Soru {question.question_number}</b> {difficulty_label}"
        elements.append(Paragraph(header, self.styles["QuestionNumber"]))

        # Soru görüntüsü
        if os.path.exists(question.file_path):
            try:
                img = Image(question.file_path)

                # Orijinal boyutları al
                img_width, img_height = img.wrap(0, 0)

                # Grid için sabit maksimum boyutlar (2x2 grid için optimize)
                max_img_width = 7 * cm   # ~8.5cm sütun genişliği için
                max_img_height = 9 * cm  # ~12.5cm satır yüksekliği için (header dahil)

                # En-boy oranını koru
                scale = min(max_img_width / img_width, max_img_height / img_height, 1.0)
                img.drawWidth = img_width * scale
                img.drawHeight = img_height * scale

                elements.append(img)
            except Exception as e:
                logger.error(f"Görüntü eklenemedi ({question.file_path}): {e}")
                elements.append(Paragraph("[Görüntü yüklenemedi]", self.styles["ExamText"]))
        else:
            elements.append(Paragraph("[Dosya bulunamadı]", self.styles["ExamText"]))

        return elements

    def _create_grid_questions(
        self,
        questions: List[SelectedQuestion],
        content_width: float,
        content_height: float,
        cols: int = 2,
        rows: int = 2
    ) -> List:
        """
        Soruları grid düzeninde oluşturur (sayfa başına cols x rows soru).

        Args:
            questions: Soru listesi
            content_width: Kullanılabilir içerik genişliği
            content_height: Kullanılabilir içerik yüksekliği
            cols: Sütun sayısı
            rows: Satır sayısı

        Returns:
            Platypus element listesi
        """
        elements = []

        # Her hücrenin boyutları - kesin ölçüler
        col_width = content_width / cols
        row_height = 11 * cm  # Her satır için sabit 11cm (2 satır = 22cm < 25.7cm sayfa içeriği)

        questions_per_page = cols * rows

        # Soruları sayfa başına grupla
        for page_start in range(0, len(questions), questions_per_page):
            page_questions = questions[page_start:page_start + questions_per_page]

            # Grid tablosu oluştur - tek tablo, tüm satırlar
            table_data = []

            for row_idx in range(rows):
                row_data = []
                has_content = False

                for col_idx in range(cols):
                    q_idx = row_idx * cols + col_idx
                    if q_idx < len(page_questions):
                        # Liste olarak hücre içeriği al
                        cell_content = self._create_question_content(
                            page_questions[q_idx], col_width, row_height
                        )
                        has_content = True
                    else:
                        # Boş hücre
                        cell_content = ""
                    row_data.append(cell_content)

                if has_content:
                    table_data.append(row_data)

            if table_data:
                # Tek tablo - rowHeights sabit
                grid_table = Table(
                    table_data,
                    colWidths=[col_width] * cols,
                    rowHeights=[row_height] * len(table_data),
                    splitByRow=0  # Satır bazında bölme
                )
                grid_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    # Dikey çizgiler
                    ("LINEAFTER", (0, 0), (cols-2, -1), 0.5, lightgrey),
                    # Yatay çizgiler
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, lightgrey),
                ]))
                elements.append(grid_table)

            elements.append(PageBreak())

        return elements

    def _create_answer_key(self, questions: List[SelectedQuestion]) -> List:
        """
        Cevap anahtarı sayfası oluşturur.

        Returns:
            Platypus element listesi
        """
        elements = []

        elements.append(PageBreak())
        elements.append(Paragraph("CEVAP ANAHTARI", self.styles["ExamTitle"]))
        elements.append(Spacer(1, 1 * cm))

        # Cevapları tablo olarak göster
        answers_data = [["Soru", "Cevap", "Kazanım", "Zorluk"]]

        for q in questions:
            answers_data.append([
                str(q.question_number),
                q.answer or "-",
                q.kazanim_code,
                q.difficulty.capitalize()
            ])

        answers_table = Table(
            answers_data,
            colWidths=[2 * cm, 2 * cm, 6 * cm, 3 * cm]
        )
        answers_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), self.bold_font),
            ("FONTNAME", (0, 1), (-1, -1), self.font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), self.LIGHT_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, gray),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))

        elements.append(answers_table)

        return elements

    def generate(
        self,
        questions: List[SelectedQuestion],
        title: str = "Çalışma Sınavı",
        include_answer_key: bool = True
    ) -> str:
        """
        Sınav PDF'i oluşturur.

        Args:
            questions: Seçilen sorular listesi
            title: Sınav başlığı
            include_answer_key: Cevap anahtarı ekle

        Returns:
            Oluşturulan PDF dosya yolu
        """
        # Dosya adı oluştur
        exam_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sinav_{timestamp}_{exam_id}.pdf"
        output_path = self.output_dir / filename

        # Zorluk dağılımını hesapla
        difficulty_distribution = {"kolay": 0, "orta": 0, "zor": 0}
        kazanimlar = set()
        for q in questions:
            if q.difficulty in difficulty_distribution:
                difficulty_distribution[q.difficulty] += 1
            kazanimlar.add(q.kazanim_code)

        # PDF oluştur
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=self.MARGIN,
            rightMargin=self.MARGIN,
            topMargin=self.MARGIN,
            bottomMargin=self.MARGIN
        )

        # İçerik oluştur
        elements = []

        # Kapak sayfası
        elements.extend(self._create_cover_page(
            title=title,
            question_count=len(questions),
            kazanimlar=list(kazanimlar),
            difficulty_distribution=difficulty_distribution
        ))

        # Sorular (2x2 grid düzen - sayfa başına 4 soru)
        content_width = self.PAGE_WIDTH - 2 * self.MARGIN
        content_height = self.PAGE_HEIGHT - 2 * self.MARGIN

        elements.extend(self._create_grid_questions(
            questions, content_width, content_height,
            cols=2, rows=2  # 4 soru/sayfa
        ))

        # Cevap anahtarı
        if include_answer_key:
            elements.extend(self._create_answer_key(questions))

        # PDF'i oluştur
        doc.build(elements)

        logger.info(f"PDF oluşturuldu: {output_path}")
        return str(output_path)

    def generate_from_files(
        self,
        file_paths: List[str],
        title: str = "Çalışma Sınavı"
    ) -> str:
        """
        Dosya yollarından direkt PDF oluşturur (analiz olmadan).

        Args:
            file_paths: Soru görüntü dosya yolları
            title: Sınav başlığı

        Returns:
            PDF dosya yolu
        """
        questions = []
        for i, path in enumerate(file_paths, 1):
            questions.append(SelectedQuestion(
                file_path=path,
                kazanim_code="N/A",
                difficulty="orta",
                answer=None,
                question_number=i
            ))

        return self.generate(questions, title)
