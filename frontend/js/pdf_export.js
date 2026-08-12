/**
 * pdf_export.js
 * Client-side PDF export for GigGuard AI — invoices and scope creep reports.
 * Uses jsPDF + html2canvas. No server call needed.
 */

const { jsPDF } = window.jspdf;

/**
 * Exports any HTML element to a downloadable PDF.
 *
 * @param {string} elementId   - The id of the HTML element to capture.
 * @param {string} filename    - Output filename, e.g. "GigGuard_Invoice_42_2024-07-01.pdf"
 * @param {Function} [onDone]  - Optional callback when export completes.
 */
async function exportElementToPDF(elementId, filename, onDone) {
  const element = document.getElementById(elementId);
  if (!element) {
    console.error(`[GigGuard PDF] Element #${elementId} not found.`);
    return;
  }

  // Show a loading indicator if one exists
  const btn = document.getElementById("export-pdf-btn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Generating PDF…";
  }

  try {
    const canvas = await html2canvas(element, {
      scale: 2,          // 2x for crisp print quality
      useCORS: true,     // allow cross-origin images (logo, etc.)
      logging: false,
    });

    const imgData = canvas.toDataURL("image/png");
    const pdf = new jsPDF({
      orientation: "portrait",
      unit: "mm",
      format: "a4",
    });

    const pageWidth  = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const imgWidth   = pageWidth;
    const imgHeight  = (canvas.height * pageWidth) / canvas.width;

    let yOffset = 0;
    let remainingHeight = imgHeight;

    // Handle multi-page: split the canvas across A4 pages
    while (remainingHeight > 0) {
      pdf.addImage(imgData, "PNG", 0, yOffset, imgWidth, imgHeight);
      remainingHeight -= pageHeight;
      if (remainingHeight > 0) {
        pdf.addPage();
        yOffset -= pageHeight;
      }
    }

    pdf.save(filename);
  } catch (err) {
    console.error("[GigGuard PDF] Export failed:", err);
    alert("PDF export failed. Please try again.");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Export as PDF";
    }
    if (typeof onDone === "function") onDone();
  }
}

/**
 * Generates a consistent filename for invoices.
 * Format: GigGuard_Invoice_{id}_{YYYY-MM-DD}.pdf
 */
function invoicePDFFilename(invoiceId) {
  const date = new Date().toISOString().split("T")[0];
  return `GigGuard_Invoice_${invoiceId}_${date}.pdf`;
}

/**
 * Generates a consistent filename for scope creep reports.
 * Format: GigGuard_ScopeCreepReport_{id}_{YYYY-MM-DD}.pdf
 */
function scopeCreepPDFFilename(reportId) {
  const date = new Date().toISOString().split("T")[0];
  return `GigGuard_ScopeCreepReport_${reportId}_${date}.pdf`;
}