(function () {
    "use strict";

    /* Autocompleta el precio unitario al elegir un producto. */
    const productSelect = document.getElementById("product_id");
    const priceInput = document.getElementById("unit_price");

    if (productSelect && priceInput) {
        const syncPrice = () => {
            const option = productSelect.selectedOptions[0];
            const price = option ? option.dataset.price : null;
            if (price !== undefined && price !== null && price !== "") {
                priceInput.value = price;
            }
        };
        productSelect.addEventListener("change", syncPrice);
    }

    /* Autocompleta tasa y tipo de cálculo en las líneas de costo. */
    const conceptSelects = document.querySelectorAll(".cost-concept");
    conceptSelects.forEach((select) => {
        const form = select.closest("form");
        if (!form) {
            return;
        }
        const calculation = form.querySelector('[name="calculation_type"]');
        const rate = form.querySelector('[name="rate"]');
        select.addEventListener("change", () => {
            const option = select.selectedOptions[0];
            if (!option) {
                return;
            }
            if (calculation && option.dataset.calculation) {
                calculation.value = option.dataset.calculation;
            }
            if (rate && option.dataset.rate) {
                rate.value = option.dataset.rate;
            }
        });
    });

    /* Abre el diálogo de impresión de la factura. */
    const printButtons = document.querySelectorAll("[data-print]");
    printButtons.forEach((button) => {
        button.addEventListener("click", () => window.print());
    });

    /* Cierra los mensajes flash después de unos segundos. */
    const flashes = document.querySelectorAll(".main > .alert");
    flashes.forEach((flash) => {
        window.setTimeout(() => {
            flash.style.transition = "opacity 400ms ease";
            flash.style.opacity = "0";
            window.setTimeout(() => flash.remove(), 450);
        }, 6000);
    });
})();
