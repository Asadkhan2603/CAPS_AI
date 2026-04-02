import Modal from '../Modal';
import FormInput from '../FormInput';

export default function DeleteReviewPrompt({
  deleteError,
  deleteReviewId,
  deleteReviewMetadata,
  deleteReviewPromptConfig,
  deleteReviewPromptOpen,
  deleteReviewTarget,
  onClose,
  onRetry,
  setDeleteReviewId,
  setDeleteReviewMetadata
}) {
  return (
    <Modal open={deleteReviewPromptOpen} title={deleteReviewPromptConfig.promptTitle} onClose={onClose}>
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="text-sm text-slate-600 dark:text-slate-300">{deleteReviewPromptConfig.promptDescription}</p>
          {deleteReviewTarget ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
              Pending delete target: <span className="font-medium">{deleteReviewTarget.name || deleteReviewTarget.code || deleteReviewTarget.id}</span>
            </div>
          ) : null}
          {deleteError ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              {deleteError}
            </div>
          ) : null}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <FormInput
            label={deleteReviewPromptConfig.label}
            value={deleteReviewId}
            placeholder={deleteReviewPromptConfig.placeholder}
            onChange={(e) => setDeleteReviewId(e.target.value)}
          />
          {deleteReviewPromptConfig.metadataFields.map((field) => (
            <FormInput
              key={field.name}
              label={field.label}
              type={field.type || 'text'}
              value={deleteReviewMetadata[field.name] ?? ''}
              placeholder={field.placeholder}
              required={field.required}
              onChange={(e) =>
                setDeleteReviewMetadata((prev) => ({
                  ...prev,
                  [field.name]: e.target.value
                }))
              }
            />
          ))}
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              if (!deleteReviewTarget) return;
              onRetry(deleteReviewTarget, { reviewId: deleteReviewId, metadata: deleteReviewMetadata });
            }}
          >
            Retry Delete
          </button>
        </div>
      </div>
    </Modal>
  );
}
