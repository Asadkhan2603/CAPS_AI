import FileUpload from '../../components/ui/FileUpload';
import FormInput from '../../components/ui/FormInput';
import { getEventRegistrationAvailability } from './eventRegistration';

export default function EventRegistrationForm({
  events = [],
  selectedEvent = null,
  selectedEventId = '',
  onSelectEvent,
  form,
  onFormChange,
  paymentReceiptFile,
  onPaymentReceiptFileChange,
  onSubmit,
  onCancel,
  submitting = false,
  showEventSelector = true,
  submitLabel = 'Submitting...',
  submitIdleLabel = 'Submit Registration',
  uploadProgress = 0,
  uploadStatus = 'idle'
}) {
  const availability = getEventRegistrationAvailability(selectedEvent);
  const paymentReceiptRequired = Boolean(selectedEvent?.payment_required);
  const submitDisabled =
    submitting ||
    !selectedEvent ||
    !availability.canRegister ||
    (paymentReceiptRequired && !form.payment_qr_code) ||
    (paymentReceiptRequired && !paymentReceiptFile);

  function updateField(name, value) {
    onFormChange((prev) => ({
      ...prev,
      [name]: value
    }));
  }

  return (
    <form className="grid gap-4 lg:grid-cols-2" onSubmit={onSubmit}>
      <div className="space-y-3">
        {showEventSelector ? (
          <FormInput
            as="select"
            label="Event"
            required
            value={selectedEventId}
            onChange={(e) => onSelectEvent?.(e.target.value)}
          >
            <option value="">Select Event</option>
            {events.map((item) => {
              const optionAvailability = getEventRegistrationAvailability(item);
              return (
                <option key={item.id} value={item.id} disabled={!optionAvailability.canRegister && item.id !== selectedEventId}>
                  {item.title || item.id}
                  {!optionAvailability.canRegister ? ` (${optionAvailability.label})` : ''}
                </option>
              );
            })}
          </FormInput>
        ) : null}

        {selectedEvent ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
            <p className="font-medium">{selectedEvent.title}</p>
            <p className="mt-1">
              {availability.canRegister
                ? 'Registration is currently open.'
                : availability.title || 'Registration is not available right now.'}
            </p>
            <p className="mt-1">
              {selectedEvent.approval_required ? 'Coordinator approval required.' : 'Instant confirmation on successful submission.'}
            </p>
            <p className="mt-1">
              If the confirmed seats are full, new registrations move to the waitlist automatically.
            </p>
            <p className="mt-1">
              {selectedEvent.payment_required ? `Payment required: INR ${selectedEvent.payment_amount ?? 0}` : 'No payment required.'}
              {selectedEvent.payment_qr_image_url ? (
                <>
                  {' '}
                  <a className="text-brand-600 underline hover:text-brand-700" href={selectedEvent.payment_qr_image_url} target="_blank" rel="noreferrer">
                    View QR
                  </a>
                </>
              ) : null}
            </p>
            <p className="mt-1">
              {selectedEvent.certificate_enabled ? 'Certificates available for marked attendees.' : 'No certificate for this event.'}
            </p>
            {selectedEvent.registration_end ? (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Registration closes: {new Date(selectedEvent.registration_end).toLocaleString()}
              </p>
            ) : null}
          </div>
        ) : null}

        <FormInput label="Enrollment Number" required value={form.enrollment_number} onChange={(e) => updateField('enrollment_number', e.target.value)} />
        <FormInput label="Full Name" required value={form.full_name} onChange={(e) => updateField('full_name', e.target.value)} />
        <FormInput label="Email" required type="email" value={form.email} onChange={(e) => updateField('email', e.target.value)} />
        <FormInput label="Year" required value={form.year} onChange={(e) => updateField('year', e.target.value)} />
        <FormInput label="Course / Branch" required value={form.course_branch} onChange={(e) => updateField('course_branch', e.target.value)} />
        <FormInput label="Class / Section" required value={form.class_name} onChange={(e) => updateField('class_name', e.target.value)} />
        <FormInput label="Phone Number" required value={form.phone_number} onChange={(e) => updateField('phone_number', e.target.value)} />
        <FormInput label="WhatsApp Number" required value={form.whatsapp_number} onChange={(e) => updateField('whatsapp_number', e.target.value)} />
        <FormInput
          label={paymentReceiptRequired ? 'Payment Reference / Transaction ID' : 'Payment Reference / Transaction ID (Optional)'}
          required={paymentReceiptRequired}
          value={form.payment_qr_code}
          onChange={(e) => updateField('payment_qr_code', e.target.value)}
        />

        <div className="flex flex-wrap justify-end gap-2 pt-2">
          {onCancel ? (
            <button type="button" className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
          ) : null}
          <button type="submit" className="btn-primary" disabled={submitDisabled} title={!availability.canRegister ? availability.title : ''}>
            {submitting ? submitLabel : submitIdleLabel}
          </button>
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Payment Receipt {paymentReceiptRequired ? '(Required)' : '(Optional)'}
          </p>
          <FileUpload
            accept=".png,.jpg,.jpeg,.pdf"
            onFileSelect={onPaymentReceiptFileChange}
            progress={uploadProgress}
            status={uploadStatus}
          />
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            {paymentReceiptFile ? `Selected file: ${paymentReceiptFile.name}` : 'Upload receipt image or PDF if payment proof is needed.'}
          </p>
        </div>
      </div>
    </form>
  );
}
