(function () {
    "use strict";

    const personTypeSelect = document.getElementById("person_type");
    const naturalFields = document.getElementById("natural-fields");
    const juridicaFields = document.getElementById("juridica-fields");

    if (!personTypeSelect || !naturalFields || !juridicaFields) {
        return;
    }

    const fullNameInput = document.getElementById("full_name");
    const cedulaInput = document.getElementById("cedula");
    const rucInput = document.getElementById("ruc");
    const razonSocialInput = document.getElementById("razon_social");

    const toggleFields = () => {
        const isNatural = personTypeSelect.value === "NATURAL";
        const isJuridica = personTypeSelect.value === "JURIDICA";

        naturalFields.hidden = !isNatural;
        juridicaFields.hidden = !isJuridica;
        fullNameInput.required = isNatural;
        cedulaInput.required = isNatural;
        rucInput.required = isJuridica;
        razonSocialInput.required = isJuridica;
    };

    personTypeSelect.addEventListener("change", toggleFields);
    toggleFields();
})();
