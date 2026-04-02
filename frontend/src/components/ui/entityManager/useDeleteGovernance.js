import { useEffect, useState } from 'react';
import { apiClient } from '../../../services/apiClient';
import { invalidateLookupCacheForPath } from '../../../services/paginatedLookups';
import { formatApiError } from '../../../utils/apiError';

function buildInitialReviewMetadata(fields = []) {
  return fields.reduce((acc, field) => {
    acc[field.name] = field.defaultValue ?? '';
    return acc;
  }, {});
}

function extractReviewRequirement(err, fallbackMessage) {
  const data = err?.response?.data ?? {};
  const detail = data?.detail;
  const errorDetail = data?.error?.detail;
  const explicitFlag =
    data?.delete_requires_review ??
    data?.error?.delete_requires_review ??
    detail?.delete_requires_review ??
    errorDetail?.delete_requires_review;

  let required = false;
  let overrides = {};

  if (typeof explicitFlag === 'boolean') {
    required = explicitFlag;
  } else if (explicitFlag && typeof explicitFlag === 'object') {
    required = explicitFlag.required ?? true;
    overrides = explicitFlag;
  }

  const textualHints = [
    fallbackMessage,
    data?.message,
    data?.error?.message,
    typeof detail === 'string' ? detail : null,
    typeof errorDetail === 'string' ? errorDetail : null
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (!required) {
    required =
      textualHints.includes('review_id') ||
      textualHints.includes('approval required') ||
      textualHints.includes('governance approval');
  }

  if (!required) {
    return { required: false, overrides: {} };
  }

  const detailObject = typeof detail === 'object' && detail !== null ? detail : {};
  const errorDetailObject = typeof errorDetail === 'object' && errorDetail !== null ? errorDetail : {};

  return {
    required: true,
    overrides: {
      label:
        overrides.label ??
        data?.review_id_label ??
        detailObject.review_id_label ??
        errorDetailObject.review_id_label,
      placeholder:
        overrides.placeholder ??
        data?.review_id_placeholder ??
        detailObject.review_id_placeholder ??
        errorDetailObject.review_id_placeholder,
      helpText:
        overrides.helpText ??
        data?.review_help_text ??
        detailObject.review_help_text ??
        errorDetailObject.review_help_text,
      promptTitle:
        overrides.promptTitle ??
        data?.review_prompt_title ??
        detailObject.review_prompt_title ??
        errorDetailObject.review_prompt_title,
      promptDescription:
        overrides.promptDescription ??
        data?.review_prompt_description ??
        detailObject.review_prompt_description ??
        errorDetailObject.review_prompt_description,
      metadataFields:
        overrides.metadataFields ??
        data?.review_metadata_fields ??
        detailObject.review_metadata_fields ??
        errorDetailObject.review_metadata_fields
    }
  };
}

export function useDeleteGovernance({
  deletePath,
  deleteReviewConfig,
  loadData,
  pushToast,
  singularTitle,
  title
}) {
  const [deleteError, setDeleteError] = useState('');
  const [deleteReviewId, setDeleteReviewId] = useState('');
  const [deleteReviewMetadata, setDeleteReviewMetadata] = useState(() => buildInitialReviewMetadata(deleteReviewConfig.metadataFields));
  const [deleteReviewPromptOpen, setDeleteReviewPromptOpen] = useState(false);
  const [deleteReviewTarget, setDeleteReviewTarget] = useState(null);
  const [deleteReviewPromptConfig, setDeleteReviewPromptConfig] = useState(deleteReviewConfig);

  useEffect(() => {
    setDeleteReviewPromptConfig(deleteReviewConfig);
    setDeleteReviewMetadata((prev) => {
      const next = buildInitialReviewMetadata(deleteReviewConfig.metadataFields);
      for (const key of Object.keys(next)) {
        if (prev[key] !== undefined) {
          next[key] = prev[key];
        }
      }
      return next;
    });
  }, [deleteReviewConfig]);

  function closeDeleteReviewPrompt() {
    setDeleteError('');
    setDeleteReviewPromptOpen(false);
    setDeleteReviewTarget(null);
    setDeleteReviewPromptConfig(deleteReviewConfig);
  }

  function buildDeleteConfig(reviewId = deleteReviewId, metadata = deleteReviewMetadata) {
    const trimmedReviewId = String(reviewId || '').trim();
    const normalizedMetadata = Object.entries(metadata || {}).reduce((acc, [key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        acc[key] = value;
      }
      return acc;
    }, {});

    const params = {};
    if (trimmedReviewId) {
      params.review_id = trimmedReviewId;
    }
    if (Object.keys(normalizedMetadata).length > 0) {
      params.review_metadata = JSON.stringify(normalizedMetadata);
    }

    return Object.keys(params).length ? { params } : undefined;
  }

  async function onDelete(row, options = {}) {
    const { reviewId = deleteReviewId, metadata = deleteReviewMetadata } = options;
    const trimmedReviewId = String(reviewId || '').trim();
    const deleteConfig = buildDeleteConfig(reviewId, metadata);

    try {
      setDeleteError('');
      await apiClient.delete(`${deletePath}/${row.id}`, deleteConfig);
      invalidateLookupCacheForPath(`${deletePath}/`);
      setDeleteError('');
      pushToast({ title: 'Deleted', description: `${singularTitle} removed.`, variant: 'success' });
      closeDeleteReviewPrompt();
      await loadData();
    } catch (err) {
      const message = formatApiError(err, `Failed to delete ${title.toLowerCase()}`);
      const governanceState = extractReviewRequirement(err, message);

      if (governanceState.required) {
        console.warn(`[EntityManager:${title}] delete blocked by governance approval`, {
          rowId: row.id,
          reviewId: trimmedReviewId || null,
          reviewMetadata: metadata,
          message
        });
        setDeleteReviewTarget(row);
        setDeleteReviewPromptConfig((prev) => ({
          ...prev,
          ...governanceState.overrides,
          metadataFields: Array.isArray(governanceState.overrides.metadataFields)
            ? governanceState.overrides.metadataFields
            : prev.metadataFields
        }));
        setDeleteReviewPromptOpen(true);
        pushToast({ title: 'Governance approval required', description: message, variant: 'warning' });
      } else {
        console.error(`[EntityManager:${title}] delete failed`, {
          rowId: row.id,
          reviewId: trimmedReviewId || null,
          reviewMetadata: metadata,
          message
        });
        pushToast({ title: 'Delete failed', description: message, variant: 'error' });
      }

      setDeleteError(message);
    }
  }

  return {
    closeDeleteReviewPrompt,
    deleteError,
    deleteReviewId,
    deleteReviewMetadata,
    deleteReviewPromptConfig,
    deleteReviewPromptOpen,
    deleteReviewTarget,
    onDelete,
    setDeleteReviewId,
    setDeleteReviewMetadata
  };
}
