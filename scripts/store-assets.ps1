param([string]$Output = 'docs/store/assets')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
if (Test-Path -LiteralPath $Output) { throw 'Choose a fresh asset directory' }
New-Item -ItemType Directory -Path $Output | Out-Null
foreach ($dimensions in @(@(440,280),@(1400,560))) {
    $width,$height = $dimensions
    $bitmap = [System.Drawing.Bitmap]::new($width,$height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.Clear([System.Drawing.ColorTranslator]::FromHtml('#17131f'))
    $scale = $height / 280.0
    $violet = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#8b5cf6'))
    $yellow = [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml('#fbbf24'))
    $white = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
    foreach ($circle in @(@(64,32,23),@(94,54,23),@(83,90,23),@(45,90,23),@(34,54,23))) {
        $graphics.FillEllipse($violet,[single](($circle[0]-$circle[2])*0.65*$scale+25*$scale),[single](($circle[1]-$circle[2])*0.65*$scale+78*$scale),[single]($circle[2]*1.3*$scale),[single]($circle[2]*1.3*$scale))
    }
    $graphics.FillEllipse($yellow,[single](56.2*$scale),[single](109.2*$scale),[single](20.8*$scale),[single](20.8*$scale))
    $title = [System.Drawing.Font]::new('Segoe UI',[single](35*$scale),[System.Drawing.FontStyle]::Bold,[System.Drawing.GraphicsUnit]::Pixel)
    $body = [System.Drawing.Font]::new('Segoe UI',[single](17*$scale),[System.Drawing.FontStyle]::Regular,[System.Drawing.GraphicsUnit]::Pixel)
    $graphics.DrawString('CueFlora',$title,$white,[single](120*$scale),[single](88*$scale))
    $graphics.DrawString("AI subtitles & translation`nfor YouTube",$body,$white,[single](120*$scale),[single](139*$scale))
    $graphics.DrawString('Your services. Your languages.',$body,$white,[single](25*$scale),[single](221*$scale))
    $target = Join-Path $Output "promo-$width`x$height.png"
    $bitmap.Save([System.IO.Path]::GetFullPath($target),[System.Drawing.Imaging.ImageFormat]::Png)
    $title.Dispose(); $body.Dispose(); $white.Dispose(); $yellow.Dispose(); $violet.Dispose(); $graphics.Dispose(); $bitmap.Dispose()
}
Copy-Item -LiteralPath public/icon/128.png -Destination (Join-Path $Output 'store-icon-128.png')
