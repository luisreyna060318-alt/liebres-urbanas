# Convierte docs/REPORTE.docx en docs/REPORTE.pdf con Microsoft Word (automatización COM).
#
# Uso (desde la raíz del repositorio, después de python docs/reporte/generar_docx.py):
#     powershell -ExecutionPolicy Bypass -File docs/reporte/convertir_pdf.ps1
#
# Abre el docx en solo lectura, actualiza los campos (número de página), lo guarda como PDF, cierra el documento y sale de Word.
# Si Word ya estaba abierto con documentos de la persona, no los toca: solo cierra el documento que abrió este script.

$ErrorActionPreference = 'Stop'

$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$docx = Join-Path $raiz 'docs\REPORTE.docx'
$pdf = Join-Path $raiz 'docs\REPORTE.pdf'

if (-not (Test-Path $docx)) {
    throw "No existe $docx. Primero corre: python docs/reporte/generar_docx.py"
}

$word = $null
$doc = $null
$habiaDocumentos = $false
try {
    $word = New-Object -ComObject Word.Application
    # Si COM nos devolvió una instancia que ya tenía documentos abiertos, es la de la persona: no se cierra al final.
    $habiaDocumentos = ($word.Documents.Count -gt 0)
    if (-not $habiaDocumentos) { $word.Visible = $false }
    $word.DisplayAlerts = 0  # wdAlertsNone

    # Open(FileName, ConfirmConversions, ReadOnly, AddToRecentFiles)
    $doc = $word.Documents.Open($docx, $false, $true, $false)

    $doc.Fields.Update() | Out-Null
    foreach ($seccion in $doc.Sections) {
        foreach ($pie in $seccion.Footers) { $pie.Range.Fields.Update() | Out-Null }
    }
    $doc.Repaginate()

    # SaveAs2(FileName, FileFormat = wdFormatPDF (17)). El documento sigue abierto en solo lectura y no se modifica.
    # (Con ExportAsFixedFormat y argumentos posicionales, Word se quedaba esperando desde PowerShell.)
    $doc.SaveAs2([string]$pdf, 17)
    $paginas = $doc.ComputeStatistics(2)  # wdStatisticPages
    Write-Output "Escrito docs\REPORTE.pdf ($paginas paginas)"
}
finally {
    if ($doc -ne $null) {
        $doc.Close(0)  # wdDoNotSaveChanges
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
    }
    if ($word -ne $null) {
        if (-not $habiaDocumentos -and $word.Documents.Count -eq 0) { $word.Quit() }
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
