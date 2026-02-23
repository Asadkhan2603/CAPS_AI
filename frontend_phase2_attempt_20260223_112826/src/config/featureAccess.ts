export type Role = 'admin' | 'teacher' | 'student';

export interface FeatureAccess {
  roles: Role[];
  requiredTeacherExtensions?: string[];
}

export const FEATURE_ACCESS: Record<string, FeatureAccess> = {
  DASHBOARD: { roles: ['admin', 'teacher', 'student'] },
  ANALYTICS: { roles: ['admin', 'teacher', 'student'] },
  HISTORY: { roles: ['admin', 'teacher', 'student'] },
  PROFILE: { roles: ['admin', 'teacher', 'student'] },
  ACADEMIC_STRUCTURE: { roles: ['admin', 'teacher', 'student'] },
  STUDENTS: { roles: ['admin', 'teacher'] },
  SUBJECTS: { roles: ['admin', 'teacher'] },
  ASSIGNMENTS: { roles: ['admin', 'teacher'] },
  SUBMISSIONS: { roles: ['admin', 'teacher', 'student'] },
  REVIEW_TICKETS: { roles: ['admin', 'teacher'] },
  EVALUATIONS: { roles: ['admin', 'teacher', 'student'] },
  ENROLLMENTS: { 
    roles: ['admin', 'teacher'],
    requiredTeacherExtensions: ['year_head', 'class_coordinator']
  },
  NOTICES: { roles: ['admin', 'teacher', 'student'] },
  CLUBS: { roles: ['admin', 'teacher', 'student'] },
  AUDIT_LOGS: { roles: ['admin', 'teacher'] },
  DEVELOPER_PANEL: { roles: ['admin'] },
  USERS: { roles: ['admin'] },
  COURSES: { roles: ['admin'] },
  DEPARTMENTS: { roles: ['admin'] },
  BRANCHES: { roles: ['admin'] },
  YEARS: { roles: ['admin'] },
  SECTIONS: { roles: ['admin', 'teacher'] },
};
