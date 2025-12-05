/**
 * Sistema de validación en tiempo real para formularios
 */

document.addEventListener('DOMContentLoaded', function() {
    // Configuración de validadores por tipo de campo
    const validators = {
        presupuesto: {
            validate: function(value) {
                if (value === '' || value === null) {
                    return { 
                        valid: false, 
                        message: 'El presupuesto es requerido' 
                    };
                }
                const numValue = parseFloat(value);
                if (isNaN(numValue)) {
                    return { 
                        valid: false, 
                        message: 'El presupuesto debe ser un número válido' 
                    };
                }
                if (numValue <= 0) {
                    return { 
                        valid: false, 
                        message: 'El presupuesto debe ser mayor que 0' 
                    };
                }
                return { valid: true };
            },
            pattern: /^-?\d+(\.\d{1,2})?$/
        },
        nombre: {
            validate: function(value) {
                if (value.trim() === '') {
                    return { 
                        valid: false, 
                        message: 'El nombre es requerido' 
                    };
                }
                if (value.trim().length < 3) {
                    return { 
                        valid: false, 
                        message: 'El nombre debe tener al menos 3 caracteres' 
                    };
                }
                return { valid: true };
            }
        },
        cliente: {
            validate: function(value) {
                if (value.trim() === '') {
                    return { 
                        valid: false, 
                        message: 'El cliente es requerido' 
                    };
                }
                return { valid: true };
            }
        },
        direccion: {
            validate: function(value) {
                if (value.trim() === '') {
                    return { 
                        valid: false, 
                        message: 'La dirección es requerida' 
                    };
                }
                return { valid: true };
            }
        },
        ciudad: {
            validate: function(value) {
                if (value.trim() === '') {
                    return { 
                        valid: false, 
                        message: 'La ciudad es requerida' 
                    };
                }
                return { valid: true };
            }
        },
        fecha_inicio: {
            validate: function(value) {
                if (value === '') {
                    return { 
                        valid: false, 
                        message: 'La fecha de inicio es requerida' 
                    };
                }
                // Comparar directamente strings en formato YYYY-MM-DD
                const today = new Date();
                const todayString = today.getFullYear() + '-' + 
                                   String(today.getMonth() + 1).padStart(2, '0') + '-' + 
                                   String(today.getDate()).padStart(2, '0');
                
                if (value < todayString) {
                    return { 
                        valid: false, 
                        message: 'La fecha de inicio no puede ser anterior al día actual' 
                    };
                }
                return { valid: true };
            }
        },
        fecha_termino: {
            validate: function(value) {
                if (value === '') return { valid: true };
                
                // Comparar directamente strings en formato YYYY-MM-DD
                const today = new Date();
                const todayString = today.getFullYear() + '-' + 
                                   String(today.getMonth() + 1).padStart(2, '0') + '-' + 
                                   String(today.getDate()).padStart(2, '0');
                
                if (value < todayString) {
                    return { 
                        valid: false, 
                        message: 'La fecha de término no puede ser anterior al día actual' 
                    };
                }
                
                const inicioInput = document.querySelector('input[name="fecha_inicio"]');
                if (inicioInput && inicioInput.value) {
                    if (value < inicioInput.value) {
                        return { 
                            valid: false, 
                            message: 'La fecha de término no puede ser anterior a la fecha de inicio' 
                        };
                    }
                }
                return { valid: true };
            }
        }
    };

    // Obtener todos los campos del formulario
    const formInputs = document.querySelectorAll('input[name], select[name], textarea[name]');
    
    formInputs.forEach(input => {
        const fieldName = input.name;
        
        // Crear contenedor para mensaje de error si no existe
        if (!input.parentElement.querySelector('.field-error')) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'field-error alert alert-danger d-none mt-2 mb-2 py-2 px-3';
            errorDiv.style.fontSize = '0.9rem';
            input.parentElement.appendChild(errorDiv);
        }

        // Agregar evento de validación en tiempo real
        input.addEventListener('blur', function() {
            validateField(input, fieldName, validators);
        });

        input.addEventListener('input', function() {
            validateField(input, fieldName, validators);
        });

        input.addEventListener('change', function() {
            validateField(input, fieldName, validators);
        });
    });

    // Validar formulario antes de enviar
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            
            const inputs = form.querySelectorAll('input[name], select[name], textarea[name]');
            inputs.forEach(input => {
                const fieldName = input.name;
                const result = validateField(input, fieldName, validators);
                if (!result.valid) {
                    isValid = false;
                }
            });

            if (!isValid) {
                e.preventDefault();
                showAlert('Por favor, corrija los errores en el formulario', 'danger');
            }
        });
    });
});

/**
 * Valida un campo individual
 * @param {HTMLElement} input - El elemento input a validar
 * @param {string} fieldName - Nombre del campo
 * @param {object} validators - Objeto con validadores
 * @returns {object} - {valid: boolean, message: string}
 */
function validateField(input, fieldName, validators) {
    const errorDiv = input.parentElement.querySelector('.field-error');
    let result = { valid: true };

    // Buscar validador para este campo
    if (validators[fieldName]) {
        result = validators[fieldName].validate(input.value);
    }

    // Mostrar/ocultar error
    if (!result.valid) {
        if (errorDiv) {
            errorDiv.textContent = result.message;
            errorDiv.classList.remove('d-none');
        }
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
    } else {
        if (errorDiv) {
            errorDiv.classList.add('d-none');
        }
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    }

    return result;
}

/**
 * Muestra una alerta en la página
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo de alerta (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const firstSection = document.querySelector('main');
    if (firstSection) {
        firstSection.insertBefore(alertDiv, firstSection.firstChild);
    }
}
