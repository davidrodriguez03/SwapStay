/* ===========================
   SwapStay – Main JS
   Alpine.js 3.x + Bootstrap 5
   =========================== */

document.addEventListener('DOMContentLoaded', () => {

    // ---- Scroll animations ----
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                e.target.classList.add('visible');
                observer.unobserve(e.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.fade-in-up').forEach(el => observer.observe(el));

    // ---- Auto-dismiss alerts ----
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(el => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
            if (bsAlert) bsAlert.close();
        }, 4000);
    });

    // ---- Form select styling ----
    document.querySelectorAll('select.form-select, select.form-control').forEach(sel => {
        sel.addEventListener('change', function() {
            this.classList.toggle('text-muted', !this.value);
        });
    });

    // ---- Date input minimum today ----
    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach(input => {
        if (!input.min) input.min = today;
    });

    // ---- Navbar active link highlight ----
    const currentPath = window.location.pathname;
    document.querySelectorAll('.navbar .nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // ---- Price formatter inputs ----
    document.querySelectorAll('input[data-format="currency"]').forEach(input => {
        input.addEventListener('blur', function() {
            const val = parseFloat(this.value.replace(/[^0-9.]/g, ''));
            if (!isNaN(val)) {
                this.value = val.toLocaleString('es-CO', { minimumFractionDigits: 0 });
            }
        });
    });

});
