(function () {
    "use strict";

    var personTypeSelect = document.getElementById("person_type");
    var naturalFields = document.getElementById("natural-fields");
    var juridicaFields = document.getElementById("juridica-fields");

    function toggleFields() {
        var value = personTypeSelect.value;
        naturalFields.hidden = value !== "NATURAL";
        juridicaFields.hidden = value !== "JURIDICA";
    }

    personTypeSelect.addEventListener("change", toggleFields);
    toggleFields();
})();
