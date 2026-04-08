export const FEATURE_ACCESS = {
  adminDashboard: { allowedRoles: ['admin'] },
  adminOnboarding: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin']
  },
  adminRbac: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin']
  },
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
  helpSupport: { allowedRoles: ['admin', 'teacher', 'student'] },
  grievancesStudent: { allowedRoles: ['student'] },
  grievancesCoordinator: {
    allowedRoles: ['teacher'],
    requiredTeacherExtensions: ['class_coordinator']
  },
  grievancesHod: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['hod']
  },
  grievancesDean: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['dean']
  },
  grievancesAssigned: { allowedRoles: ['admin', 'teacher'] },
  grievancesFallback: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['academic_admin', 'super_admin']
  },
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
  studentBulkImport: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin']
  },
  coordinatorStudentMapping: {
    allowedRoles: ['teacher'],
    requiredTeacherExtensions: ['class_coordinator']
  },
  clubs: { allowedRoles: ['admin', 'teacher', 'student'] },
  clubEvents: { allowedRoles: ['admin', 'teacher'] },
  eventRegistrations: { allowedRoles: ['admin', 'teacher', 'student'] },
  auditLogs: {
    allowedRoles: ['admin', 'teacher'],
    requiredAdminTypes: ['super_admin', 'admin', 'compliance_admin']
  },
  developerPanel: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin']
  },
  users: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin']
  },
  universities: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin']
  },
  faculties: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin']
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
  batches: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'department_admin']
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
  },
  adminSections: {
    allowedRoles: ['admin'],
    requiredAdminTypes: ['super_admin', 'admin', 'academic_admin', 'department_admin'],
    deleteGovernance: {
      enabled: true,
      promptDescription: 'Section deletes require governance approval before the archive can proceed.',
      metadataFields: [
        { name: 'reason', label: 'Delete Reason', placeholder: 'Why is this section being archived?' },
        { name: 'replacement_section', label: 'Replacement Section', placeholder: 'Optional replacement section or migration target' }
      ]
    }
  },
  teacherSections: {
    allowedRoles: ['teacher']
  }
};
