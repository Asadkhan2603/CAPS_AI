export const FEATURE_ACCESS = {
  adminDashboard: { allowedRoles: ['admin'] },
  adminGovernance: { allowedRoles: ['admin'] },
  adminAcademicStructure: { allowedRoles: ['admin'] },
  adminOperations: { allowedRoles: ['admin'] },
  adminClubs: { allowedRoles: ['admin'] },
  adminCommunication: { allowedRoles: ['admin'] },
  adminCompliance: { allowedRoles: ['admin'] },
  adminAnalytics: { allowedRoles: ['admin'] },
  adminSystem: { allowedRoles: ['admin'] },
  adminRecovery: { allowedRoles: ['admin'] },
  adminDeveloper: { allowedRoles: ['admin'] },
  dashboard: { allowedRoles: ['admin', 'teacher', 'student'] },
  analytics: { allowedRoles: ['admin', 'teacher', 'student'] },
  history: { allowedRoles: ['admin', 'teacher', 'student'] },
  timetable: { allowedRoles: ['admin', 'teacher', 'student'] },
  profile: { allowedRoles: ['admin', 'teacher', 'student'] },
  academicStructure: { allowedRoles: ['admin', 'teacher', 'student'] },
  students: { allowedRoles: ['admin', 'teacher'] },
  groups: { allowedRoles: ['admin', 'teacher'] },
  subjects: { allowedRoles: ['admin', 'teacher'] },
  courseOfferings: { allowedRoles: ['admin', 'teacher'] },
  classSlots: { allowedRoles: ['admin', 'teacher', 'student'] },
  attendanceRecords: { allowedRoles: ['admin', 'teacher', 'student'] },
  assignments: { allowedRoles: ['admin', 'teacher'] },
  submissions: { allowedRoles: ['admin', 'teacher', 'student'] },
  aiModule: { allowedRoles: ['admin', 'teacher'] },
  reviewTickets: { allowedRoles: ['admin', 'teacher'] },
  evaluations: { allowedRoles: ['admin', 'teacher', 'student'] },
  enrollments: {
    allowedRoles: ['admin', 'teacher'],
    requiredTeacherExtensions: ['year_head', 'class_coordinator']
  },
  communicationFeed: { allowedRoles: ['admin', 'teacher', 'student'] },
  communicationAnnouncements: { allowedRoles: ['admin', 'teacher', 'student'] },
  communicationMessages: { allowedRoles: ['admin', 'teacher', 'student'] },
  notices: { allowedRoles: ['admin', 'teacher', 'student'] },
  notifications: { allowedRoles: ['admin', 'teacher', 'student'] },
  clubs: { allowedRoles: ['admin', 'teacher', 'student'] },
  clubEvents: { allowedRoles: ['admin', 'teacher', 'student'] },
  eventRegistrations: { allowedRoles: ['admin', 'teacher', 'student'] },
  auditLogs: { allowedRoles: ['admin', 'teacher'] },
  developerPanel: { allowedRoles: ['admin'] },
  users: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin']
  },
  faculties: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin']
  },
  courses: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin'],
    deleteGovernance: {
      enabled: true,
      promptDescription: 'Course deletes are governance-gated. Provide the approved review_id before retrying the archive request.',
      metadataFields: [
        { name: 'reason', label: 'Delete Reason', placeholder: 'Why is this course being archived?' }
      ]
    }
  },
  programs: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'department_admin']
  },
  departments: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin'],
    deleteGovernance: {
      enabled: true,
      promptDescription: 'Department deletes require governance approval because related branches and dependent academic records may also be archived.',
      metadataFields: [
        { name: 'reason', label: 'Delete Reason', placeholder: 'Why is this department being archived?' },
        { name: 'impact_note', label: 'Impact Note', placeholder: 'List dependent entities or migration notes' }
      ]
    }
  },
  specializations: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'department_admin']
  },
  branches: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin'],
    deleteGovernance: {
      enabled: true,
      promptDescription: 'Branch deletes require an approved governance review. Capture the business reason before retrying.',
      metadataFields: [
        { name: 'reason', label: 'Delete Reason', placeholder: 'Why is this branch being archived?' }
      ]
    }
  },
  batches: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'department_admin']
  },
  years: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin'],
    deleteGovernance: {
      enabled: true,
      promptDescription: 'Year deletes are protected by governance review because downstream academic assignments may depend on them.',
      metadataFields: [
        { name: 'reason', label: 'Delete Reason', placeholder: 'Why is this year record being archived?' }
      ]
    }
  },
  semesters: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'department_admin']
  },
  sections: {
    allowedRoles: ['admin', 'teacher'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'department_admin'],
    deleteGovernance: {
      enabled: true,
      promptDescription: 'Section deletes require governance approval before the archive can proceed.',
      metadataFields: [
        { name: 'reason', label: 'Delete Reason', placeholder: 'Why is this section being archived?' },
        { name: 'replacement_section', label: 'Replacement Section', placeholder: 'Optional replacement section or migration target' }
      ]
    }
  }
};
