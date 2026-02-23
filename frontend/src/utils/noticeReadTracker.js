function keyForUser(userId) {
  return `caps_ai_notice_read_${userId || 'anonymous'}`;
}

function readMap(userId) {
  try {
    const raw = localStorage.getItem(keyForUser(userId));
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeMap(userId, map) {
  localStorage.setItem(keyForUser(userId), JSON.stringify(map));
}

export function isNoticeRead(userId, noticeId) {
  if (!noticeId) return false;
  const map = readMap(userId);
  return Boolean(map[noticeId]);
}

export function markNoticeRead(userId, noticeId) {
  if (!noticeId) return;
  const map = readMap(userId);
  map[noticeId] = Date.now();
  writeMap(userId, map);
}

export function markNoticesRead(userId, noticeIds = []) {
  if (!Array.isArray(noticeIds) || noticeIds.length === 0) return;
  const map = readMap(userId);
  const now = Date.now();
  noticeIds.forEach((id) => {
    if (id) map[id] = now;
  });
  writeMap(userId, map);
}

export function unreadNoticeCount(userId, notices = []) {
  const map = readMap(userId);
  return (notices || []).filter((item) => item?.id && !map[item.id]).length;
}

