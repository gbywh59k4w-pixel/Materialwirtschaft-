(function () {
    var input = document.getElementById("scan-input");
    if (input) {
        input.focus();
    }

    var toggleBtn = document.getElementById("camera-toggle");
    var readerDiv = document.getElementById("qr-reader");
    if (!toggleBtn || !readerDiv) return;

    var html5QrCode = null;
    var running = false;

    toggleBtn.addEventListener("click", function () {
        if (running) {
            stopCamera();
            return;
        }
        readerDiv.style.display = "block";
        html5QrCode = new Html5Qrcode("qr-reader");
        html5QrCode
            .start(
                { facingMode: "environment" },
                { fps: 10, qrbox: 250 },
                function onScanSuccess(decodedText) {
                    input.value = decodedText;
                    stopCamera();
                    document.getElementById("scan-form").submit();
                }
            )
            .then(function () {
                running = true;
                toggleBtn.textContent = "⏹ Kamera stoppen";
            })
            .catch(function (err) {
                readerDiv.innerHTML = "<p class='text-danger'>Kamera konnte nicht gestartet werden: " + err + "</p>";
            });
    });

    function stopCamera() {
        if (html5QrCode && running) {
            html5QrCode.stop().then(function () {
                html5QrCode.clear();
                readerDiv.style.display = "none";
                toggleBtn.textContent = "📷 Kamera-Scanner starten";
                running = false;
            });
        }
    }
})();
