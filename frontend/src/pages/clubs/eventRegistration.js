import { apiClient } from '../../services/apiClient';

export function getEventRegistrationAvailability(eventRow, nowValue = Date.now()) {
  if (!eventRow) {
    return {
      canRegister: false,
      disabled: true,
      label: 'Select Event',
      title: 'Choose an event first',
      reason: 'no_event'
    };
  }

  const isOpenStatus = eventRow.status === 'open';
  const startsAt = eventRow.registration_start ? new Date(eventRow.registration_start).getTime() : null;
  const endsAt = eventRow.registration_end ? new Date(eventRow.registration_end).getTime() : null;
  const notStarted = startsAt && nowValue < startsAt;
  const expired = endsAt && nowValue > endsAt;

  if (!isOpenStatus) {
    return {
      canRegister: false,
      disabled: true,
      label: eventRow.status === 'draft' ? 'Not Open' : 'Closed',
      title: `Event status is ${eventRow.status}`,
      reason: 'status_closed'
    };
  }

  if (!eventRow.registration_enabled) {
    return {
      canRegister: false,
      disabled: true,
      label: 'Registration Off',
      title: 'Registration is disabled for this event',
      reason: 'registration_disabled'
    };
  }

  if (notStarted) {
    return {
      canRegister: false,
      disabled: true,
      label: 'Not Started',
      title: `Registration opens at ${new Date(eventRow.registration_start).toLocaleString()}`,
      reason: 'registration_not_started'
    };
  }

  if (expired) {
    return {
      canRegister: false,
      disabled: true,
      label: 'Closed',
      title: 'Registration deadline passed',
      reason: 'registration_expired'
    };
  }

  return {
    canRegister: true,
    disabled: false,
    label: 'Register',
    title: '',
    reason: 'open'
  };
}

export function buildEventRegistrationFormData({ eventId, registrationForm, paymentReceiptFile }) {
  const formData = new FormData();
  formData.append('event_id', eventId);
  formData.append('enrollment_number', registrationForm.enrollment_number);
  formData.append('full_name', registrationForm.full_name);
  formData.append('email', registrationForm.email);
  formData.append('year', registrationForm.year);
  formData.append('course_branch', registrationForm.course_branch);
  formData.append('class_name', registrationForm.class_name);
  formData.append('phone_number', registrationForm.phone_number);
  formData.append('whatsapp_number', registrationForm.whatsapp_number);
  formData.append('payment_qr_code', registrationForm.payment_qr_code || '');

  if (paymentReceiptFile) {
    formData.append('payment_receipt', paymentReceiptFile);
  }

  return formData;
}

export async function submitEventRegistration({ registrationEvent, registrationForm, paymentReceiptFile }) {
  const formData = buildEventRegistrationFormData({
    eventId: registrationEvent.id,
    registrationForm,
    paymentReceiptFile
  });

  const response = await apiClient.post('/event-registrations/submit', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
}
