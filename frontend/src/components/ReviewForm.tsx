import { useEffect, useId, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { Review, ReviewStatus } from "../api/contracts";
import { useDrawer, useServiceStatus } from "../app/providers";
import { localDateTime, REVIEW_LABEL } from "../lib/format";
import { IconCheck, IconError } from "./icons";

const MAX = 4000;

/**
 * Create or update the single review attached to a finding. Drafts are never discarded on failure;
 * a stale version returns 409 and the reviewer chooses how to resolve it.
 */
export function ReviewForm({ findingId, review, onSaved, autoFocus }: {
  findingId: string; review: Review | null | undefined; onSaved?: (r: Review) => void; autoFocus?: boolean;
}) {
  const id = useId();
  const { notifyChanged } = useDrawer();
  const { state } = useServiceStatus();
  const [current, setCurrent] = useState<Review | null>(review ?? null);
  const [status, setStatus] = useState<ReviewStatus>(review?.status ?? "FOLLOW_UP_REQUESTED");
  const [note, setNote] = useState(review?.note ?? "");
  const [date, setDate] = useState(review?.follow_up_date ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<Review | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  const [edited, setEdited] = useState(false);
  useEffect(() => {
    // With live sync, newer versions arrive while the form is open. If the reviewer has unsaved edits we
    // keep the version their draft is based on, so saving surfaces a 409 instead of overwriting silently.
    if (edited) return;
    setCurrent(review ?? null);
    if (review) {
      setStatus(review.status);
      setNote(review.note);
      setDate(review.follow_up_date ?? "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [review]);

  const offline = state === "SERVICE_UNAVAILABLE";
  const noteInvalid = note.trim().length === 0;
  const edit = <T,>(setter: (v: T) => void) => (v: T) => { setEdited(true); setSavedAt(null); setter(v); };
  const dirty = !current || current.status !== status || current.note !== note || (current.follow_up_date ?? "") !== date;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (noteInvalid || saving || offline) return;
    setSaving(true);
    setError(null);
    setSavedAt(null);
    try {
      let saved: Review;
      if (!current) {
        const res = await api.createReview({ finding_id: findingId, status, note, follow_up_date: date || null });
        if (!res.created) {
          // A review already existed (e.g. saved from another tab). Keep the draft and ask the reviewer.
          setCurrent(res.review);
          setConflict(res.review);
          setSaving(false);
          return;
        }
        saved = res.review;
      } else {
        const res = await api.patchReview(current.id, {
          version: current.version, status, note,
          ...(date ? { follow_up_date: date } : { clear_follow_up_date: true }),
        });
        saved = res.review;
      }
      setCurrent(saved);
      setConflict(null);
      setEdited(false);
      setSavedAt(saved.updated_at);
      notifyChanged();
      onSaved?.(saved);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const latest = (err.details as { current?: Review }).current ?? null;
        setConflict(latest);
      } else {
        setError(err instanceof ApiError ? err.message : "Saving failed. Your draft is kept; try again.");
      }
    } finally {
      setSaving(false);
    }
  }

  function loadLatest() {
    if (!conflict) return;
    setCurrent(conflict);
    setStatus(conflict.status);
    setNote(conflict.note);
    setDate(conflict.follow_up_date ?? "");
    setConflict(null);
  }
  function keepDraft() {
    if (!conflict) return;
    setCurrent(conflict); // adopt the latest version number; the draft fields stay as typed
    setConflict(null);
  }

  return (
    <form className="stack" onSubmit={submit} noValidate aria-describedby={`${id}-scope`}>
      <p id={`${id}-scope`} className="small muted">
        Your own note. Status is an administrative workflow state, not the subject's medical status. Saved only on this computer.
      </p>
      <div className="field">
        <label className="field-label" htmlFor={`${id}-status`}>Review status</label>
        <select id={`${id}-status`} className="select" value={status} onChange={(e) => edit(setStatus)(e.target.value as ReviewStatus)}>
          {(Object.keys(REVIEW_LABEL) as ReviewStatus[]).map((s) => <option key={s} value={s}>{REVIEW_LABEL[s]}</option>)}
        </select>
      </div>
      <div className="field">
        <label className="field-label" htmlFor={`${id}-note`}>Reviewer note <span className="muted">(required)</span></label>
        <textarea id={`${id}-note`} className="textarea" value={note} maxLength={MAX} autoFocus={autoFocus}
          placeholder="e.g. Request repeat measurement / discuss with qualified medical staff"
          aria-invalid={touched && noteInvalid} aria-describedby={`${id}-count ${id}-noteerr`}
          onChange={(e) => edit(setNote)(e.target.value)} onBlur={() => setTouched(true)} />
        <div className="field-hint" id={`${id}-count`}>{note.length} / {MAX} characters</div>
        {touched && noteInvalid ? <div className="small" style={{ color: "var(--error)" }} id={`${id}-noteerr`}>Write a short note before saving.</div> : <span id={`${id}-noteerr`} />}
      </div>
      <div className="field">
        <label className="field-label" htmlFor={`${id}-date`}>Follow-up date <span className="muted">(optional, reviewer-chosen)</span></label>
        <input id={`${id}-date`} type="date" className="input" value={date} onChange={(e) => edit(setDate)(e.target.value)} />
      </div>

      {conflict ? (
        <div className="alert alert-review" role="alert">
          <IconError />
          <div className="stack" style={{ gap: 8 }}>
            <strong>This review changed elsewhere (now version {conflict.version}, {REVIEW_LABEL[conflict.status]}).</strong>
            <span>Your draft is still here. Saved note: “{conflict.note.length > 140 ? `${conflict.note.slice(0, 140)}…` : conflict.note}”</span>
            <div className="btn-row">
              <button type="button" className="btn btn-secondary btn-sm" onClick={loadLatest}>Load saved version</button>
              <button type="button" className="btn btn-secondary btn-sm" onClick={keepDraft}>Keep my draft, then save again</button>
            </div>
          </div>
        </div>
      ) : null}
      {error ? <div className="alert alert-error" role="alert"><IconError /><div>{error} <button type="submit" className="btn btn-secondary btn-sm" style={{ marginLeft: 8 }}>Retry</button></div></div> : null}

      <div className="btn-row">
        <button type="submit" className="btn btn-primary" disabled={saving || offline || !!conflict || (!!current && !dirty)}
          aria-describedby={offline ? `${id}-offline` : undefined}>
          {saving ? "Saving…" : current ? "Save changes" : "Save follow-up"}
        </button>
        {offline ? <span id={`${id}-offline`} className="small" style={{ color: "var(--error)" }}>Saving is disabled while the local service is unavailable.</span> : null}
        {current && !dirty && !savedAt ? <span className="small muted">No unsaved changes.</span> : null}
      </div>
      <div aria-live="polite" className="live-region">
        {savedAt ? (
          <span className="badge badge-success"><IconCheck />Saved locally · {localDateTime(savedAt)}</span>
        ) : current ? (
          <span className="small muted">Last saved {localDateTime(current.updated_at)} · version {current.version}</span>
        ) : null}
      </div>
    </form>
  );
}
