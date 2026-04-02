import { useEffect, useState } from 'react';
import { formatApiError } from '../../utils/apiError';
import { createInitialRegistrationForm } from './constants';

export function useClubRegistrationFlow({ user, onSubmitRegistration, pushToast }) {
  const [registrationModalOpen, setRegistrationModalOpen] = useState(false);
  const [registrationEvent, setRegistrationEvent] = useState(null);
  const [registrationForm, setRegistrationForm] = useState(createInitialRegistrationForm(user));
  const [paymentReceiptFile, setPaymentReceiptFile] = useState(null);
  const [registrationSubmitting, setRegistrationSubmitting] = useState(false);

  useEffect(() => {
    setRegistrationForm((prev) => ({
      ...prev,
      full_name: prev.full_name || user?.full_name || '',
      email: prev.email || user?.email || ''
    }));
  }, [user]);

  function closeRegistrationModal() {
    setRegistrationModalOpen(false);
    setRegistrationEvent(null);
    setPaymentReceiptFile(null);
  }

  function openRegistrationModal(eventRow) {
    setRegistrationEvent(eventRow);
    setRegistrationForm(createInitialRegistrationForm(user));
    setPaymentReceiptFile(null);
    setRegistrationModalOpen(true);
  }

  async function submitEventRegistrationForm(event) {
    event.preventDefault();
    if (!registrationEvent) return;

    if (registrationEvent.payment_required && !registrationForm.payment_qr_code) {
      pushToast({ title: 'Payment required', description: 'Enter transaction reference.', variant: 'error' });
      return;
    }
    if (registrationEvent.payment_required && !paymentReceiptFile) {
      pushToast({ title: 'Payment screenshot required', description: 'Upload payment screenshot.', variant: 'error' });
      return;
    }

    setRegistrationSubmitting(true);
    try {
      await onSubmitRegistration({
        paymentReceiptFile,
        registrationEvent,
        registrationForm
      });
      closeRegistrationModal();
      setRegistrationForm(createInitialRegistrationForm(user));
    } catch (err) {
      pushToast({
        title: 'Registration failed',
        description: formatApiError(err, 'Could not register for event'),
        variant: 'error'
      });
    } finally {
      setRegistrationSubmitting(false);
    }
  }

  return {
    closeRegistrationModal,
    openRegistrationModal,
    paymentReceiptFile,
    registrationEvent,
    registrationForm,
    registrationModalOpen,
    registrationSubmitting,
    setPaymentReceiptFile,
    setRegistrationForm,
    submitEventRegistrationForm
  };
}
