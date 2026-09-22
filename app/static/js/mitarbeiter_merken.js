(function () {
    var select = document.getElementById("mitarbeiter-select");
    if (!select) return;
    var key = "mw_letzter_mitarbeiter";

    try {
        var letzter = localStorage.getItem(key);
        if (letzter) {
            for (var i = 0; i < select.options.length; i++) {
                if (select.options[i].value === letzter) {
                    select.value = letzter;
                    break;
                }
            }
        }
    } catch (e) {
        /* localStorage nicht verfügbar - kein Problem, einfach ohne Vorauswahl weiter */
    }

    select.addEventListener("change", function () {
        try {
            localStorage.setItem(key, select.value);
        } catch (e) {
            /* ignorieren */
        }
    });

    var mengeInput = document.getElementById("menge-input");
    if (mengeInput) {
        mengeInput.focus();
        mengeInput.select();
    }
})();
