import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuth } from '../contexts/AuthContext';
import { bookProjectsApi } from '../services/bookProjectsApi';
import { getApiUrl } from '../utils/getApiUrl';
import { ExportPaywallModal } from '../components/payments/ExportPaywallModal';
import { PrintOrderButton } from '../components/print';
import { AddRecipeModal } from '../components/book-projects/AddRecipeModal';
import type { BookProjectExport, ProjectShareLink, ProjectSubmission } from '../types';

const PROJECT_TYPE_COPY: Record<string, string> = {
  wedding: 'Wedding cookbook',
  anniversary: 'Anniversary cookbook',
  heirloom: 'Family heirloom',
  memorial: 'Memorial cookbook',
  holiday: 'Holiday cookbook',
  general: 'Cookbook project',
};

export const ProjectDashboardPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const projectId = Number(id);

  const { data: project, isLoading, error } = useQuery({
    queryKey: ['book-project', projectId],
    queryFn: () => bookProjectsApi.get(projectId),
    enabled: isAuthenticated && !!projectId,
  });

  const { data: submissions } = useQuery({
    queryKey: ['book-project-submissions', projectId],
    queryFn: () => bookProjectsApi.listSubmissions(projectId),
    enabled: isAuthenticated && !!projectId,
  });

  if (authLoading) return null;
  if (!isAuthenticated) {
    navigate('/login');
    return null;
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div
          className="h-24 rounded-lg animate-pulse"
          style={{ backgroundColor: '#f6efe6' }}
        />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <p className="mb-3" style={{ color: '#9b644b' }}>
          Project not found.
        </p>
        <button
          onClick={() => navigate('/projects')}
          className="px-4 py-2 text-white rounded-lg"
          style={{ backgroundColor: '#f15f1c' }}
        >
          Back to projects
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <button
        onClick={() => navigate('/projects')}
        className="text-sm hover:underline"
        style={{ color: '#9b644b' }}
      >
        ← Back to projects
      </button>

      <header>
        <div className="text-xs uppercase tracking-wider mb-1" style={{ color: '#9b644b' }}>
          {PROJECT_TYPE_COPY[project.project_type] ?? 'Cookbook project'}
        </div>
        <h1 className="text-3xl font-bold" style={{ color: '#1c120d' }}>
          {project.title}
        </h1>
        {project.honorees && project.honorees.length > 0 && (
          <p className="mt-1" style={{ color: '#6b5a52' }}>
            For {project.honorees.join(' & ')}
            {project.occasion_date ? ` — ${project.occasion_date}` : ''}
          </p>
        )}
        <div className="mt-3 inline-flex items-center px-2 py-1 rounded text-xs"
          style={{ backgroundColor: '#f6efe6', color: '#6b5a52' }}>
          Status: {project.status}
        </div>
      </header>

      <ShareLinksSection
        projectId={projectId}
        shareLinks={project.share_links ?? []}
        onChange={() =>
          queryClient.invalidateQueries({ queryKey: ['book-project', projectId] })
        }
      />

      <SubmissionsSection
        projectId={projectId}
        submissions={submissions ?? []}
        currentUserId={user?.id}
        onChange={() =>
          queryClient.invalidateQueries({
            queryKey: ['book-project-submissions', projectId],
          })
        }
      />

      <ExportSection projectId={projectId} projectTitle={project.title} />
    </div>
  );
};

const ShareLinksSection: React.FC<{
  projectId: number;
  shareLinks: ProjectShareLink[];
  onChange: () => void;
}> = ({ projectId, shareLinks, onChange }) => {
  const createMutation = useMutation({
    mutationFn: () => bookProjectsApi.createShareLink(projectId, {}),
    onSuccess: onChange,
  });
  const revokeMutation = useMutation({
    mutationFn: (token: string) => bookProjectsApi.revokeShareLink(projectId, token),
    onSuccess: onChange,
  });

  const apiBase = getApiUrl();
  const frontendOrigin = typeof window !== 'undefined' ? window.location.origin : '';

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-semibold" style={{ color: '#1c120d' }}>
          Share links
        </h2>
        <button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
          className="px-3 py-1.5 text-sm text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
          style={{ backgroundColor: '#f15f1c' }}
        >
          {createMutation.isPending ? 'Creating…' : 'New share link'}
        </button>
      </div>

      {shareLinks.length === 0 ? (
        <p className="text-sm" style={{ color: '#9b644b' }}>
          Generate a share link to invite contributors. Anyone with the link can submit
          a recipe — no account required on their end.
        </p>
      ) : (
        <ul className="space-y-2">
          {shareLinks.map((link) => {
            const url = link.url ?? `${frontendOrigin}/contribute/${link.token}`;
            return (
              <li
                key={link.id}
                className="px-3 py-2 rounded-lg border flex items-center justify-between gap-3"
                style={{
                  borderColor: '#e8dccf',
                  backgroundColor: link.revoked ? '#f6efe6' : '#fffbf5',
                  opacity: link.revoked ? 0.6 : 1,
                }}
              >
                <div className="min-w-0">
                  <div className="text-sm font-mono truncate" style={{ color: '#1c120d' }}>
                    {url}
                  </div>
                  <div className="text-xs mt-0.5" style={{ color: '#9b644b' }}>
                    {link.submission_count} submissions
                    {link.submission_cap ? ` / ${link.submission_cap}` : ''}
                    {link.revoked ? ' • revoked' : ''}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      if (typeof navigator !== 'undefined' && navigator.clipboard) {
                        navigator.clipboard.writeText(url);
                      }
                    }}
                    className="px-2 py-1 text-xs rounded hover:opacity-80"
                    style={{ backgroundColor: '#1c120d', color: '#fffbf5' }}
                  >
                    Copy
                  </button>
                  {!link.revoked && (
                    <button
                      onClick={() => revokeMutation.mutate(link.token)}
                      className="px-2 py-1 text-xs rounded hover:opacity-80"
                      style={{ color: '#9b3a1c' }}
                    >
                      Revoke
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {/* Avoid unused-var warning while keeping `apiBase` available for future absolute-URL UX. */}
      <span style={{ display: 'none' }}>{apiBase}</span>
    </section>
  );
};

const SubmissionsSection: React.FC<{
  projectId: number;
  submissions: ProjectSubmission[];
  currentUserId: number | undefined;
  onChange: () => void;
}> = ({ projectId, submissions, currentUserId, onChange }) => {
  const [addOpen, setAddOpen] = useState(false);

  const toggleMutation = useMutation({
    mutationFn: ({ recipeId, excluded }: { recipeId: number; excluded: boolean }) =>
      bookProjectsApi.setSubmissionExcluded(projectId, recipeId, excluded),
    onSuccess: onChange,
  });

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-semibold" style={{ color: '#1c120d' }}>
          Submissions
        </h2>
        <button
          onClick={() => setAddOpen(true)}
          className="px-3 py-1.5 text-sm text-white rounded-lg hover:opacity-90 transition-opacity"
          style={{ backgroundColor: '#f15f1c' }}
        >
          Add a recipe
        </button>
      </div>

      {submissions.length === 0 ? (
        <p className="text-sm" style={{ color: '#9b644b' }}>
          No recipes yet. Add one yourself, or share the link above so family and friends
          can submit theirs.
        </p>
      ) : (
        <ul className="space-y-2">
          {submissions.map((sub) => {
            const isMine =
              !sub.contributor &&
              currentUserId !== undefined &&
              sub.uploaded_by_id === currentUserId;
            const attribution = sub.contributor
              ? `From ${sub.contributor.display_name}`
              : isMine
                ? 'Added by you'
                : 'Anonymous';
            return (
              <li
                key={sub.recipe_id}
                className="px-3 py-3 rounded-lg border flex items-start justify-between gap-3"
                style={{
                  borderColor: '#e8dccf',
                  backgroundColor: sub.is_excluded_from_project ? '#f6efe6' : '#fffbf5',
                  opacity: sub.is_excluded_from_project ? 0.6 : 1,
                }}
              >
                <div className="min-w-0">
                  <div className="font-medium truncate" style={{ color: '#1c120d' }}>
                    {sub.title}
                  </div>
                  <div className="text-xs mt-0.5" style={{ color: '#9b644b' }}>
                    {attribution}
                    {sub.is_excluded_from_project ? ' • excluded from book' : ''}
                  </div>
                </div>
                <button
                  onClick={() =>
                    toggleMutation.mutate({
                      recipeId: sub.recipe_id,
                      excluded: !sub.is_excluded_from_project,
                    })
                  }
                  className="px-2 py-1 text-xs rounded hover:opacity-80 whitespace-nowrap"
                  style={{
                    backgroundColor: sub.is_excluded_from_project ? '#f15f1c' : '#e8dccf',
                    color: sub.is_excluded_from_project ? '#fff' : '#1c120d',
                  }}
                >
                  {sub.is_excluded_from_project ? 'Include' : 'Exclude'}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <AddRecipeModal
        projectId={projectId}
        isOpen={addOpen}
        onClose={() => setAddOpen(false)}
        onSubmitted={() => {
          setAddOpen(false);
          onChange();
        }}
      />
    </section>
  );
};

const ExportSection: React.FC<{ projectId: number; projectTitle: string }> = ({
  projectId,
  projectTitle,
}) => {
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [paywallOpen, setPaywallOpen] = useState(false);
  const [pendingPaidExportId, setPendingPaidExportId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const previewMutation = useMutation({
    mutationFn: () => bookProjectsApi.createPreview(projectId),
    onSuccess: async (resp) => {
      setPreviewError(null);
      try {
        await bookProjectsApi.downloadExport(
          projectId,
          resp.export.id,
          `book-project-${projectId}-preview.pdf`,
        );
      } catch (err) {
        setPreviewError(err instanceof Error ? err.message : 'Download failed');
      }
      queryClient.invalidateQueries({ queryKey: ['book-project-exports', projectId] });
    },
    onError: (err: Error) => {
      setPreviewError(err.message);
    },
  });

  // Poll the exports list when we're waiting on a paid PDF to finish rendering.
  // Stripe's webhook fires server-side and renders the PDF; the client doesn't
  // get a direct signal, so we just refetch every couple seconds until the
  // pdf_file_path appears.
  const { data: exports } = useQuery({
    queryKey: ['book-project-exports', projectId],
    queryFn: () => bookProjectsApi.listExports(projectId),
    enabled: !!projectId,
    refetchInterval: pendingPaidExportId ? 2500 : false,
  });

  // Wait for is_ready to flip true server-side (the Stripe webhook ran, the
  // PDF rendered, storage fields populated). Without this check the row
  // exists from the moment the PaymentIntent was created and the dashboard
  // would offer a broken download that 202s.
  const paidReadyExport: BookProjectExport | undefined = exports?.find(
    (e) => e.id === pendingPaidExportId && !e.is_watermarked && e.is_ready,
  );

  // Project is "unlocked" if any export carries a payment_id — that paid row
  // is the original purchase. Subsequent free regenerations don't have a
  // payment_id of their own but inherit the unlock.
  const hasPaidClean = (exports ?? []).some(
    (e) => !e.is_watermarked && e.payment_id !== null,
  );

  // For the Download button: the most recent clean export that's actually
  // ready (paid OR regenerated). Sorting client-side; exports are typically
  // few per project so the cost is negligible.
  const latestReadyClean: BookProjectExport | undefined = [...(exports ?? [])]
    .filter((e) => !e.is_watermarked && e.is_ready)
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0];

  const regenerateMutation = useMutation({
    mutationFn: () => bookProjectsApi.regenerateCleanExport(projectId),
    onSuccess: () => {
      setPreviewError(null);
      queryClient.invalidateQueries({ queryKey: ['book-project-exports', projectId] });
    },
    onError: (err: Error) => {
      setPreviewError(err.message);
    },
  });

  return (
    <section>
      <h2 className="text-xl font-semibold mb-3" style={{ color: '#1c120d' }}>
        Export
      </h2>
      <div
        className="px-4 py-4 rounded-lg border"
        style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
      >
        <p className="text-sm mb-3" style={{ color: '#6b5a52' }}>
          Download a watermarked PDF preview for free. The clean (no watermark) version is
          a one-time purchase.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => previewMutation.mutate()}
            disabled={previewMutation.isPending}
            className="px-4 py-2 rounded-lg border hover:opacity-90 disabled:opacity-50 transition-opacity"
            style={{
              borderColor: '#1c120d',
              backgroundColor: '#fffbf5',
              color: '#1c120d',
            }}
          >
            {previewMutation.isPending ? 'Rendering…' : 'Download preview PDF'}
          </button>

          {/* Mid-purchase, before webhook completes. */}
          {pendingPaidExportId && !paidReadyExport && (
            <span
              className="px-4 py-2 text-sm rounded-lg"
              style={{ backgroundColor: '#f6efe6', color: '#6b5a52' }}
            >
              Rendering clean PDF…
            </span>
          )}

          {/* Project is unlocked: offer download (always) and regenerate
              (after the user adds more recipes / edits the project). */}
          {hasPaidClean && latestReadyClean && (
            <>
              <button
                onClick={() => {
                  bookProjectsApi
                    .downloadExport(
                      projectId,
                      latestReadyClean.id,
                      `book-project-${projectId}.pdf`,
                    )
                    .catch((err) => {
                      setPreviewError(
                        err instanceof Error ? err.message : 'Download failed',
                      );
                    });
                }}
                className="px-4 py-2 text-white rounded-lg hover:opacity-90 transition-opacity"
                style={{ backgroundColor: '#1c120d' }}
              >
                Download clean PDF
              </button>
              <button
                onClick={() => regenerateMutation.mutate()}
                disabled={regenerateMutation.isPending}
                className="px-4 py-2 rounded-lg border hover:opacity-90 disabled:opacity-50 transition-opacity"
                style={{
                  borderColor: '#1c120d',
                  backgroundColor: '#fffbf5',
                  color: '#1c120d',
                }}
                title="Re-render the clean PDF with your latest recipes (free, you've already paid)."
              >
                {regenerateMutation.isPending ? 'Regenerating…' : 'Regenerate clean PDF'}
              </button>
            </>
          )}

          {/* Never paid yet — show the paywall CTA. */}
          {!hasPaidClean && !pendingPaidExportId && (
            <button
              onClick={() => setPaywallOpen(true)}
              className="px-4 py-2 text-white rounded-lg hover:opacity-90 transition-opacity"
              style={{ backgroundColor: '#f15f1c' }}
            >
              Buy clean PDF
            </button>
          )}
        </div>
        {previewError && (
          <div
            className="mt-3 px-3 py-2 rounded text-sm"
            style={{ backgroundColor: '#fef0ea', color: '#9b3a1c' }}
          >
            {previewError}
          </div>
        )}

        <div
          className="mt-4 pt-4 border-t"
          style={{ borderColor: '#e8dccf' }}
        >
          <p className="text-sm mb-2" style={{ color: '#6b5a52' }}>
            Or have it professionally printed and shipped — bound paperback, your
            choice of trim and quantity.
          </p>
          <PrintOrderButton
            entityType="book_project"
            entityId={projectId}
            entityTitle={projectTitle}
            buttonText="Order printed book"
            variant="outline"
          />
        </div>
      </div>

      <ExportPaywallModal
        projectId={projectId}
        isOpen={paywallOpen}
        onClose={() => setPaywallOpen(false)}
        onPaymentSucceeded={(exportId) => {
          setPaywallOpen(false);
          setPendingPaidExportId(exportId);
          queryClient.invalidateQueries({
            queryKey: ['book-project-exports', projectId],
          });
        }}
      />
    </section>
  );
};

export default ProjectDashboardPage;
