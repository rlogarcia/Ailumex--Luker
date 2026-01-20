/**
 * Benglish Academy - Password Reset Modal
 * Gestiona el flujo de recuperación de contraseña con stepper de 3 pasos
 */

(function() {
    'use strict';

    // Estado de la aplicación
    let currentStep = 1;
    let identification = '';
    let resetToken = '';
    let cooldownInterval = null;

    // Elementos del DOM
    const modal = document.getElementById('password-reset-modal');
    const forgotPasswordLink = document.getElementById('forgot-password-link');
    const closeModalBtn = document.getElementById('close-modal-btn');
    
    // Paso 1
    const step1Content = document.getElementById('step-1');
    const identificationInput = document.getElementById('identification-number');
    const sendCodeBtn = document.getElementById('send-code-btn');
    const cancelStep1Btn = document.getElementById('cancel-step-1-btn');
    const step1Error = document.getElementById('step-1-error');
    const step1ErrorText = document.getElementById('step-1-error-text');
    const emailHint = document.getElementById('email-hint');
    const emailHintText = document.getElementById('email-hint-text');
    
    // Paso 2
    const step2Content = document.getElementById('step-2');
    const otpInput = document.getElementById('otp-code');
    const verifyCodeBtn = document.getElementById('verify-code-btn');
    const backToStep1Btn = document.getElementById('back-to-step-1-btn');
    const resendCodeBtn = document.getElementById('resend-code-btn');
    const cooldownTimer = document.getElementById('cooldown-timer');
    const cooldownSeconds = document.getElementById('cooldown-seconds');
    const emailDisplay = document.getElementById('email-display');
    const step2Error = document.getElementById('step-2-error');
    const step2ErrorText = document.getElementById('step-2-error-text');
    
    // Paso 3
    const step3Content = document.getElementById('step-3');
    const newPasswordInput = document.getElementById('new-password');
    const confirmPasswordInput = document.getElementById('confirm-password');
    const updatePasswordBtn = document.getElementById('update-password-btn');
    const cancelStep3Btn = document.getElementById('cancel-step-3-btn');
    const step3Error = document.getElementById('step-3-error');
    const step3ErrorText = document.getElementById('step-3-error-text');
    const passwordStrength = document.getElementById('password-strength');
    const strengthFill = document.getElementById('strength-fill');
    const strengthText = document.getElementById('strength-text');
    
    // Paso de éxito
    const stepSuccess = document.getElementById('step-success');
    const closeSuccessBtn = document.getElementById('close-success-btn');

    /**
     * Inicialización de event listeners
     */
    function init() {
        // Abrir modal
        if (forgotPasswordLink) {
            forgotPasswordLink.addEventListener('click', function(e) {
                e.preventDefault();
                openModal();
            });
        }

        // Cerrar modal
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', closeModal);
        }
        
        // Cerrar al hacer click fuera del modal
        modal.querySelector('.benglish-modal-overlay').addEventListener('click', closeModal);

        // Paso 1: Enviar código
        sendCodeBtn.addEventListener('click', handleSendCode);
        cancelStep1Btn.addEventListener('click', closeModal);
        identificationInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSendCode();
            }
        });

        // Paso 2: Verificar código
        verifyCodeBtn.addEventListener('click', handleVerifyCode);
        backToStep1Btn.addEventListener('click', function() {
            goToStep(1);
        });
        resendCodeBtn.addEventListener('click', handleResendCode);
        otpInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleVerifyCode();
            }
        });
        
        // Solo permitir números en el OTP
        otpInput.addEventListener('input', function(e) {
            this.value = this.value.replace(/[^0-9]/g, '');
        });

        // Paso 3: Actualizar contraseña
        updatePasswordBtn.addEventListener('click', handleUpdatePassword);
        cancelStep3Btn.addEventListener('click', closeModal);
        
        // Toggle de visibilidad de contraseña
        document.querySelectorAll('.benglish-password-toggle').forEach(toggle => {
            toggle.addEventListener('click', function() {
                const targetId = this.getAttribute('data-target');
                const input = document.getElementById(targetId);
                const icon = this.querySelector('i');
                
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.classList.remove('fa-eye');
                    icon.classList.add('fa-eye-slash');
                    this.setAttribute('aria-label', 'Ocultar contraseña');
                } else {
                    input.type = 'password';
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                    this.setAttribute('aria-label', 'Mostrar contraseña');
                }
            });
        });
        
        // Validación de fuerza de contraseña
        newPasswordInput.addEventListener('input', updatePasswordStrength);
        
        // Paso de éxito: Cerrar
        closeSuccessBtn.addEventListener('click', function() {
            closeModal();
            location.reload(); // Recargar para volver al login
        });
    }

    /**
     * Abrir el modal
     */
    function openModal() {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        goToStep(1);
        resetForm();
    }

    /**
     * Cerrar el modal
     */
    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = '';
        resetForm();
        if (cooldownInterval) {
            clearInterval(cooldownInterval);
        }
    }

    /**
     * Resetear el formulario
     */
    function resetForm() {
        identificationInput.value = '';
        otpInput.value = '';
        newPasswordInput.value = '';
        confirmPasswordInput.value = '';
        hideError(step1Error);
        hideError(step2Error);
        hideError(step3Error);
        emailHint.style.display = 'none';
        currentStep = 1;
        identification = '';
        resetToken = '';
    }

    /**
     * Navegar a un paso específico
     */
    function goToStep(step) {
        currentStep = step;
        
        // Ocultar todos los contenidos
        document.querySelectorAll('.benglish-step-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // Mostrar el contenido del paso actual
        const stepContent = document.getElementById('step-' + step);
        if (stepContent) {
            stepContent.classList.add('active');
        }
        
        // Actualizar el stepper visual
        updateStepper(step);
        
        // Focus en el input correspondiente
        setTimeout(() => {
            if (step === 1) identificationInput.focus();
            else if (step === 2) otpInput.focus();
            else if (step === 3) newPasswordInput.focus();
        }, 100);
    }

    /**
     * Actualizar el indicador visual del stepper
     */
    function updateStepper(activeStep) {
        document.querySelectorAll('.benglish-step').forEach(step => {
            const stepNumber = parseInt(step.getAttribute('data-step'));
            
            if (stepNumber < activeStep) {
                step.classList.add('completed');
                step.classList.remove('active');
            } else if (stepNumber === activeStep) {
                step.classList.add('active');
                step.classList.remove('completed');
            } else {
                step.classList.remove('active', 'completed');
            }
        });
    }

    /**
     * Mostrar error
     */
    function showError(errorElement, textElement, message) {
        textElement.textContent = message;
        errorElement.style.display = 'flex';
    }

    /**
     * Ocultar error
     */
    function hideError(errorElement) {
        errorElement.style.display = 'none';
    }

    /**
     * Mostrar spinner en botón
     */
    function showButtonSpinner(button) {
        const btnText = button.querySelector('.btn-text');
        const btnSpinner = button.querySelector('.btn-spinner');
        if (btnText) btnText.style.display = 'none';
        if (btnSpinner) btnSpinner.style.display = 'inline-block';
        button.disabled = true;
    }

    /**
     * Ocultar spinner en botón
     */
    function hideButtonSpinner(button) {
        const btnText = button.querySelector('.btn-text');
        const btnSpinner = button.querySelector('.btn-spinner');
        if (btnText) btnText.style.display = 'inline';
        if (btnSpinner) btnSpinner.style.display = 'none';
        button.disabled = false;
    }

    /**
     * Paso 1: Enviar código OTP
     */
    async function handleSendCode() {
        hideError(step1Error);
        emailHint.style.display = 'none';
        
        identification = identificationInput.value.trim();
        
        if (!identification) {
            showError(step1Error, step1ErrorText, 'Por favor, ingresa tu número de identificación.');
            identificationInput.focus();
            return;
        }

        showButtonSpinner(sendCodeBtn);

        try {
            const response = await fetch('/benglish/password/request_otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        identification: identification,
                        identification_type: ''
                    }
                })
            });

            const data = await response.json();
            const result = data.result || data;

            if (result.success) {
                // Mostrar email ofuscado si está disponible
                if (result.email) {
                    emailHintText.textContent = 'Si existe una cuenta, recibirás un código en: ' + result.email;
                    emailHint.style.display = 'flex';
                    emailDisplay.textContent = result.email;
                } else {
                    emailDisplay.textContent = 'tu correo registrado';
                }
                
                // Ir al paso 2
                setTimeout(() => {
                    goToStep(2);
                    startCooldown(60);
                }, 1500);
            } else {
                showError(step1Error, step1ErrorText, result.message || 'Error al enviar el código. Intenta nuevamente.');
            }
        } catch (error) {
            console.error('Error:', error);
            showError(step1Error, step1ErrorText, 'Error de conexión. Por favor, verifica tu conexión e intenta nuevamente.');
        } finally {
            hideButtonSpinner(sendCodeBtn);
        }
    }

    /**
     * Paso 2: Verificar código OTP
     */
    async function handleVerifyCode() {
        hideError(step2Error);
        
        const otpCode = otpInput.value.trim();
        
        if (!otpCode) {
            showError(step2Error, step2ErrorText, 'Por favor, ingresa el código de verificación.');
            otpInput.focus();
            return;
        }
        
        if (otpCode.length !== 6) {
            showError(step2Error, step2ErrorText, 'El código debe ser de 6 dígitos.');
            otpInput.focus();
            return;
        }

        showButtonSpinner(verifyCodeBtn);

        try {
            const response = await fetch('/benglish/password/verify_otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        identification: identification,
                        otp_code: otpCode
                    }
                })
            });

            const data = await response.json();
            const result = data.result || data;

            if (result.success) {
                resetToken = result.reset_token;
                
                // Ir al paso 3
                setTimeout(() => {
                    goToStep(3);
                }, 800);
            } else {
                showError(step2Error, step2ErrorText, result.message || 'Código incorrecto. Intenta nuevamente.');
                otpInput.value = '';
                otpInput.focus();
                
                // Si expiró, mostrar opción de reenvío
                if (result.expired) {
                    resendCodeBtn.style.display = 'inline-block';
                    cooldownTimer.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showError(step2Error, step2ErrorText, 'Error de conexión. Por favor, intenta nuevamente.');
        } finally {
            hideButtonSpinner(verifyCodeBtn);
        }
    }

    /**
     * Paso 2: Reenviar código
     */
    async function handleResendCode() {
        hideError(step2Error);
        
        // Verificar cooldown
        try {
            const cooldownResponse = await fetch('/benglish/password/check_cooldown', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        identification: identification
                    }
                })
            });
            
            const cooldownData = await cooldownResponse.json();
            const cooldownResult = cooldownData.result || cooldownData;
            
            if (!cooldownResult.can_resend) {
                showError(step2Error, step2ErrorText, cooldownResult.message);
                return;
            }
        } catch (error) {
            console.error('Error checking cooldown:', error);
        }

        // Reenviar código
        const originalText = resendCodeBtn.textContent;
        resendCodeBtn.textContent = 'Reenviando...';
        resendCodeBtn.disabled = true;

        try {
            const response = await fetch('/benglish/password/request_otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        identification: identification,
                        identification_type: ''
                    }
                })
            });

            const data = await response.json();
            const result = data.result || data;

            if (result.success) {
                showError(step2Error, step2ErrorText, '✓ Código reenviado exitosamente.');
                step2Error.classList.remove('benglish-alert-error');
                step2Error.classList.add('benglish-alert-success');
                
                setTimeout(() => {
                    hideError(step2Error);
                    step2Error.classList.remove('benglish-alert-success');
                    step2Error.classList.add('benglish-alert-error');
                }, 3000);
                
                startCooldown(60);
                otpInput.value = '';
                otpInput.focus();
            } else {
                showError(step2Error, step2ErrorText, result.message || 'Error al reenviar el código.');
            }
        } catch (error) {
            console.error('Error:', error);
            showError(step2Error, step2ErrorText, 'Error de conexión. Por favor, intenta nuevamente.');
        } finally {
            resendCodeBtn.textContent = originalText;
            resendCodeBtn.disabled = false;
        }
    }

    /**
     * Iniciar cooldown para reenvío de código
     */
    function startCooldown(seconds) {
        let remaining = seconds;
        
        resendCodeBtn.style.display = 'none';
        cooldownTimer.style.display = 'inline-block';
        cooldownSeconds.textContent = remaining;
        
        if (cooldownInterval) {
            clearInterval(cooldownInterval);
        }
        
        cooldownInterval = setInterval(() => {
            remaining--;
            cooldownSeconds.textContent = remaining;
            
            if (remaining <= 0) {
                clearInterval(cooldownInterval);
                resendCodeBtn.style.display = 'inline-block';
                cooldownTimer.style.display = 'none';
            }
        }, 1000);
    }

    /**
     * Paso 3: Actualizar contraseña
     */
    async function handleUpdatePassword() {
        hideError(step3Error);
        
        const newPassword = newPasswordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        if (!newPassword) {
            showError(step3Error, step3ErrorText, 'Por favor, ingresa tu nueva contraseña.');
            newPasswordInput.focus();
            return;
        }
        
        if (newPassword.length < 6) {
            showError(step3Error, step3ErrorText, 'La contraseña debe tener al menos 6 caracteres.');
            newPasswordInput.focus();
            return;
        }
        
        if (!confirmPassword) {
            showError(step3Error, step3ErrorText, 'Por favor, confirma tu contraseña.');
            confirmPasswordInput.focus();
            return;
        }
        
        if (newPassword !== confirmPassword) {
            showError(step3Error, step3ErrorText, 'Las contraseñas no coinciden.');
            confirmPasswordInput.focus();
            return;
        }

        showButtonSpinner(updatePasswordBtn);

        try {
            const response = await fetch('/benglish/password/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        identification: identification,
                        reset_token: resetToken,
                        new_password: newPassword,
                        confirm_password: confirmPassword
                    }
                })
            });

            const data = await response.json();
            const result = data.result || data;

            if (result.success) {
                // Mostrar mensaje de éxito
                stepSuccess.classList.add('active');
                step3Content.classList.remove('active');
                updateStepper(4); // Opcional: marcar como completado
            } else {
                showError(step3Error, step3ErrorText, result.message || 'Error al actualizar la contraseña.');
            }
        } catch (error) {
            console.error('Error:', error);
            showError(step3Error, step3ErrorText, 'Error de conexión. Por favor, intenta nuevamente.');
        } finally {
            hideButtonSpinner(updatePasswordBtn);
        }
    }

    /**
     * Actualizar indicador de fuerza de contraseña
     */
    function updatePasswordStrength() {
        const password = newPasswordInput.value;
        
        if (!password) {
            passwordStrength.style.display = 'none';
            return;
        }
        
        passwordStrength.style.display = 'block';
        
        let strength = 0;
        let text = '';
        let color = '';
        
        // Calcular fuerza
        if (password.length >= 6) strength++;
        if (password.length >= 10) strength++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[^a-zA-Z0-9]/.test(password)) strength++;
        
        // Determinar texto y color
        if (strength <= 1) {
            text = 'Débil';
            color = '#dc3545';
        } else if (strength <= 3) {
            text = 'Media';
            color = '#ffc107';
        } else {
            text = 'Fuerte';
            color = '#28a745';
        }
        
        const percentage = (strength / 5) * 100;
        strengthFill.style.width = percentage + '%';
        strengthFill.style.backgroundColor = color;
        strengthText.textContent = text;
        strengthText.style.color = color;
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
