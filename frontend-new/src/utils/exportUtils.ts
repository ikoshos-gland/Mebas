/**
 * Export Utilities
 * Functions for exporting data to Excel and PDF formats
 */
import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

interface StudentProgressData {
  student_name: string;
  student_email: string;
  mastered_count: number;
  learning_count: number;
  not_started_count: number;
  mastery_percentage: number;
}

interface KazanimProgressData {
  kazanim_code: string;
  kazanim_text: string;
  subject: string;
  mastered_count: number;
  learning_count: number;
  total_students: number;
}

interface ClassProgressExportData {
  classroom_name: string;
  grade: number;
  subject: string | null;
  student_progress: StudentProgressData[];
  kazanim_progress: KazanimProgressData[];
  summary: {
    total_students: number;
    avg_mastery: number;
    total_kazanimlar: number;
  };
}

/**
 * Export classroom progress to Excel file
 */
export const exportToExcel = (data: ClassProgressExportData): void => {
  const workbook = XLSX.utils.book_new();

  // Summary sheet
  const summaryData = [
    ['Sinif Ilerleme Raporu'],
    [],
    ['Sinif Adi', data.classroom_name],
    ['Sinif', `${data.grade}. Sinif`],
    ['Ders', data.subject || 'Tum Dersler'],
    [],
    ['Toplam Ogrenci', data.summary.total_students],
    ['Ortalama Basari', `%${data.summary.avg_mastery.toFixed(1)}`],
    ['Toplam Kazanim', data.summary.total_kazanimlar],
  ];
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Ozet');

  // Student progress sheet
  const studentHeaders = ['Ogrenci Adi', 'E-posta', 'Uzman', 'Ogreniyor', 'Baslamadi', 'Basari %'];
  const studentRows = data.student_progress.map((s) => [
    s.student_name,
    s.student_email,
    s.mastered_count,
    s.learning_count,
    s.not_started_count,
    `%${s.mastery_percentage.toFixed(1)}`,
  ]);
  const studentData = [studentHeaders, ...studentRows];
  const studentSheet = XLSX.utils.aoa_to_sheet(studentData);
  XLSX.utils.book_append_sheet(workbook, studentSheet, 'Ogrenci Ilerlemesi');

  // Kazanim progress sheet
  const kazanimHeaders = ['Kazanim Kodu', 'Kazanim', 'Ders', 'Uzman', 'Ogreniyor', 'Toplam', 'Basari %'];
  const kazanimRows = data.kazanim_progress.map((k) => {
    const masteryPercent = k.total_students > 0 ? (k.mastered_count / k.total_students) * 100 : 0;
    return [
      k.kazanim_code,
      k.kazanim_text,
      k.subject,
      k.mastered_count,
      k.learning_count,
      k.total_students,
      `%${masteryPercent.toFixed(1)}`,
    ];
  });
  const kazanimData = [kazanimHeaders, ...kazanimRows];
  const kazanimSheet = XLSX.utils.aoa_to_sheet(kazanimData);
  XLSX.utils.book_append_sheet(workbook, kazanimSheet, 'Kazanim Ilerlemesi');

  // Set column widths
  studentSheet['!cols'] = [{ wch: 25 }, { wch: 30 }, { wch: 10 }, { wch: 12 }, { wch: 12 }, { wch: 12 }];
  kazanimSheet['!cols'] = [{ wch: 15 }, { wch: 50 }, { wch: 15 }, { wch: 10 }, { wch: 12 }, { wch: 10 }, { wch: 12 }];

  // Generate filename with date
  const date = new Date().toISOString().split('T')[0];
  const filename = `${data.classroom_name.replace(/\s+/g, '_')}_ilerleme_${date}.xlsx`;

  // Download
  XLSX.writeFile(workbook, filename);
};

/**
 * Export classroom progress to PDF file
 */
export const exportToPDF = (data: ClassProgressExportData): void => {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();

  // Title
  doc.setFontSize(18);
  doc.text('Sinif Ilerleme Raporu', pageWidth / 2, 20, { align: 'center' });

  // Classroom info
  doc.setFontSize(12);
  doc.text(`Sinif: ${data.classroom_name}`, 14, 35);
  doc.text(`${data.grade}. Sinif ${data.subject ? `- ${data.subject}` : ''}`, 14, 42);

  // Summary stats
  doc.setFontSize(11);
  doc.text(`Toplam Ogrenci: ${data.summary.total_students}`, 14, 55);
  doc.text(`Ortalama Basari: %${data.summary.avg_mastery.toFixed(1)}`, 80, 55);
  doc.text(`Toplam Kazanim: ${data.summary.total_kazanimlar}`, 150, 55);

  // Student progress table
  doc.setFontSize(14);
  doc.text('Ogrenci Ilerlemesi', 14, 70);

  autoTable(doc, {
    startY: 75,
    head: [['Ogrenci', 'Uzman', 'Ogreniyor', 'Baslamadi', 'Basari']],
    body: data.student_progress.map((s) => [
      s.student_name,
      s.mastered_count.toString(),
      s.learning_count.toString(),
      s.not_started_count.toString(),
      `%${s.mastery_percentage.toFixed(0)}`,
    ]),
    styles: { fontSize: 9, cellPadding: 2 },
    headStyles: { fillColor: [59, 130, 246] },
    alternateRowStyles: { fillColor: [241, 245, 249] },
  });

  // Kazanim progress table (new page)
  doc.addPage();
  doc.setFontSize(14);
  doc.text('Kazanim Ilerlemesi', 14, 20);

  autoTable(doc, {
    startY: 25,
    head: [['Kod', 'Kazanim', 'Uzman', 'Ogreniyor', 'Basari']],
    body: data.kazanim_progress.map((k) => {
      const masteryPercent = k.total_students > 0 ? (k.mastered_count / k.total_students) * 100 : 0;
      return [
        k.kazanim_code,
        k.kazanim_text.length > 60 ? k.kazanim_text.substring(0, 60) + '...' : k.kazanim_text,
        k.mastered_count.toString(),
        k.learning_count.toString(),
        `%${masteryPercent.toFixed(0)}`,
      ];
    }),
    styles: { fontSize: 8, cellPadding: 2 },
    headStyles: { fillColor: [59, 130, 246] },
    alternateRowStyles: { fillColor: [241, 245, 249] },
    columnStyles: {
      0: { cellWidth: 25 },
      1: { cellWidth: 90 },
      2: { cellWidth: 20 },
      3: { cellWidth: 25 },
      4: { cellWidth: 20 },
    },
  });

  // Footer
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.text(
      `Sayfa ${i} / ${pageCount} - ${new Date().toLocaleDateString('tr-TR')}`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 10,
      { align: 'center' }
    );
  }

  // Download
  const date = new Date().toISOString().split('T')[0];
  const filename = `${data.classroom_name.replace(/\s+/g, '_')}_ilerleme_${date}.pdf`;
  doc.save(filename);
};
