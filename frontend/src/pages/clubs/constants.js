export const tabs = [
  { key: 'overview', label: 'Overview' },
  { key: 'members', label: 'Members' },
  { key: 'events', label: 'Events' },
  { key: 'announcements', label: 'Announcements' },
  { key: 'analytics', label: 'Analytics' }
];

export const ALL_CLUBS_VALUE = '__all__';

export const clubStatusOptions = ['draft', 'pending_activation', 'active', 'registration_closed', 'closed', 'suspended', 'archived', 'dormant'];
export const activeClubStatuses = new Set(['active', 'registration_closed']);

export const initialCreateForm = {
  name: '',
  description: '',
  category: '',
  academic_year: '',
  membership_type: 'approval_required',
  max_members: '',
  coordinator_user_id: '',
  status: 'draft'
};

export const initialEventForm = {
  title: '',
  description: '',
  event_type: 'workshop',
  visibility: 'public',
  registration_start: '',
  registration_end: '',
  event_date: '',
  capacity: 100,
  registration_enabled: true,
  payment_required: false,
  payment_qr_image_url: '',
  payment_amount: ''
};

export function createInitialRegistrationForm(user = null) {
  return {
    enrollment_number: '',
    full_name: user?.full_name || '',
    email: user?.email || '',
    year: '',
    course_branch: '',
    class_name: '',
    phone_number: '',
    whatsapp_number: '',
    payment_qr_code: ''
  };
}
