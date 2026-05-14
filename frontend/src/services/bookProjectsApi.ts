import type {
  BookProject,
  BookProjectExport,
  GuestContributor,
  PreviewExportResponse,
  ProjectShareLink,
  ProjectStatus,
  ProjectSubmission,
  ProjectType,
  PurchaseExportResponse,
} from '../types';
import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';

interface CreateProjectInput {
  title: string;
  project_type?: ProjectType;
  subtitle?: string;
  dedication?: string;
  honorees?: string[];
  occasion_date?: string;
  submission_deadline?: string;
  cover_image_url?: string;
  metadata?: Record<string, unknown>;
}

interface UpdateProjectInput extends Partial<CreateProjectInput> {
  status?: ProjectStatus;
}

interface CreateShareLinkInput {
  expires_at?: string;
  submission_cap?: number;
}

interface GuestSubmissionPayload {
  display_name?: string;
  email?: string;
}

interface GuestTextSubmission extends GuestSubmissionPayload {
  text: string;
}

interface GuestUrlSubmission extends GuestSubmissionPayload {
  url: string;
}

interface PublicProjectInfo {
  project: {
    id: number;
    title: string;
    subtitle: string | null;
    project_type: ProjectType;
    honorees: string[];
    occasion_date: string | null;
    submission_deadline: string | null;
    dedication: string | null;
    cover_image_url: string | null;
  };
  share_link: {
    submission_count: number;
    submission_cap: number | null;
    expires_at: string | null;
  };
}

class BookProjectsApi {
  private _baseUrl: string | undefined;

  private get baseUrl(): string {
    if (!this._baseUrl) {
      this._baseUrl = getApiUrl();
      if (!this._baseUrl) {
        console.error('API URL undefined, defaulting to /api');
        this._baseUrl = '/api';
      }
    }
    return this._baseUrl;
  }

  // --- Organizer (auth required) ----------------------------------------

  async list(): Promise<BookProject[]> {
    const res = await apiFetch(`${this.baseUrl}/book-projects/`, { method: 'GET' });
    if (!res.ok) throw new Error('Failed to load projects');
    const data = await res.json();
    return data.projects;
  }

  async get(id: number): Promise<BookProject> {
    const res = await apiFetch(`${this.baseUrl}/book-projects/${id}`, {
      method: 'GET',
    });
    if (!res.ok) {
      if (res.status === 404) throw new Error('Project not found');
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    return data.project;
  }

  async create(input: CreateProjectInput): Promise<BookProject> {
    const res = await apiFetch(`${this.baseUrl}/book-projects/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to create project');
    }
    const data = await res.json();
    return data.project;
  }

  async update(id: number, input: UpdateProjectInput): Promise<BookProject> {
    const res = await apiFetch(`${this.baseUrl}/book-projects/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to update project');
    }
    const data = await res.json();
    return data.project;
  }

  async remove(id: number): Promise<void> {
    const res = await apiFetch(`${this.baseUrl}/book-projects/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete project');
  }

  // --- Share links -------------------------------------------------------

  async createShareLink(
    projectId: number,
    input: CreateShareLinkInput = {},
  ): Promise<ProjectShareLink> {
    const res = await apiFetch(
      `${this.baseUrl}/book-projects/${projectId}/share-links`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to create share link');
    }
    const data = await res.json();
    return data.share_link;
  }

  async revokeShareLink(projectId: number, token: string): Promise<ProjectShareLink> {
    const res = await apiFetch(
      `${this.baseUrl}/book-projects/${projectId}/share-links/${token}`,
      { method: 'DELETE' },
    );
    if (!res.ok) throw new Error('Failed to revoke share link');
    const data = await res.json();
    return data.share_link;
  }

  // --- Submissions -------------------------------------------------------

  async listSubmissions(projectId: number): Promise<ProjectSubmission[]> {
    const res = await apiFetch(
      `${this.baseUrl}/book-projects/${projectId}/submissions`,
      { method: 'GET' },
    );
    if (!res.ok) throw new Error('Failed to load submissions');
    const data = await res.json();
    return data.submissions;
  }

  async setSubmissionExcluded(
    projectId: number,
    recipeId: number,
    excluded: boolean,
  ): Promise<void> {
    const res = await apiFetch(
      `${this.baseUrl}/book-projects/${projectId}/submissions/${recipeId}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_excluded_from_project: excluded }),
      },
    );
    if (!res.ok) throw new Error('Failed to update submission');
  }

  // --- Exports -----------------------------------------------------------

  async listExports(projectId: number): Promise<BookProjectExport[]> {
    const res = await apiFetch(
      `${this.baseUrl}/book-projects/${projectId}/exports`,
      { method: 'GET' },
    );
    if (!res.ok) throw new Error('Failed to load exports');
    const data = await res.json();
    return data.exports;
  }

  async createPreview(projectId: number): Promise<PreviewExportResponse> {
    const res = await apiFetch(
      `${this.baseUrl}/book-projects/${projectId}/export/preview`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to generate preview');
    }
    return res.json();
  }

  async createPurchaseIntent(projectId: number): Promise<PurchaseExportResponse> {
    const res = await apiFetch(
      `${this.baseUrl}/book-projects/${projectId}/export/purchase`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to start purchase');
    }
    return res.json();
  }

  exportDownloadUrl(projectId: number, exportId: number): string {
    return `${this.baseUrl}/book-projects/${projectId}/exports/${exportId}/download`;
  }

  // --- Guest (no auth, share-token path) --------------------------------

  async fetchPublicByToken(token: string): Promise<PublicProjectInfo> {
    const res = await fetch(`${this.baseUrl}/book-projects/by-token/${token}`, {
      method: 'GET',
    });
    if (!res.ok) {
      if (res.status === 404) throw new Error('Invalid link');
      if (res.status === 403) throw new Error('This link is no longer active');
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  }

  async submitTextByToken(
    token: string,
    input: GuestTextSubmission,
  ): Promise<{ submission: { recipe_id: number; title: string; contributor: GuestContributor } }> {
    const res = await fetch(
      `${this.baseUrl}/book-projects/by-token/${token}/submit-text`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to submit recipe');
    }
    return res.json();
  }

  async submitUrlByToken(
    token: string,
    input: GuestUrlSubmission,
  ): Promise<{ submission: { recipe_id: number; title: string; contributor: GuestContributor } }> {
    const res = await fetch(
      `${this.baseUrl}/book-projects/by-token/${token}/submit-url`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to submit recipe');
    }
    return res.json();
  }

  async submitImageByToken(
    token: string,
    file: File,
    payload: GuestSubmissionPayload = {},
  ): Promise<{ submission: { job_id: number; image_id: number; status: string; contributor: GuestContributor } }> {
    const form = new FormData();
    form.append('image', file);
    if (payload.display_name) form.append('display_name', payload.display_name);
    if (payload.email) form.append('email', payload.email);

    const res = await fetch(
      `${this.baseUrl}/book-projects/by-token/${token}/submit-image`,
      {
        method: 'POST',
        body: form,
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to submit image');
    }
    return res.json();
  }
}

export const bookProjectsApi = new BookProjectsApi();
