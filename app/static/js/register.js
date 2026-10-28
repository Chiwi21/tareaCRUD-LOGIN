(function () {
    "use strict";

    var personTypeSelect = document.getElementById("person_type");
    var naturalFields = document.getElementById("natural-fields");
    var juridicaFields = document.getElementById("juridica-fields");

    if (!personTypeSelect || !naturalFields || !juridicaFields) {
        return;
    }

    var fullNameInput = document.getElementById("full_name");
    var cedulaInput = document.getElementById("cedula");
    var rucInput = document.getElementById("ruc");
    var razonSocialInput = document.getElementById("razon_social");

    function toggleFields() {
        var isNatural = personTypeSelect.value === "NATURAL";
        var isJuridica = personTypeSelect.value === "JURIDICA";

        naturalFields.hidden = !isNatural;
        juridicaFields.hidden = !isJuridica;
        fullNameInput.required = isNatural;
        cedulaInput.required = isNatural;
        rucInput.required = isJuridica;
        razonSocialInput.required = isJuridica;
    }

    personTypeSelect.addEventListener("change", toggleFields);
    toggleFields();
})();
