import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  EnisaEventDetail,
  isoToDatetimeLocal,
  datetimeLocalToIso,
} from '../EnisaEventDetail';
import type { EnisaEventDetail as EnisaEventDetailData } from '@/api/enisa';

const {
  getEnisaEventMock,
  confirmEnisaEventMock,
  dismissEnisaEventMock,
  reopenEnisaEventMock,
  closeEnisaEventMock,
  submitEnisaMilestoneMock,
  saveEnisaDraftMock,
  setEnisaCorrectiveDateMock,
  exportEnisaMilestoneMock,
} = vi.hoisted(() => ({
  getEnisaEventMock: vi.fn(),
  confirmEnisaEventMock: vi.fn(),
  dismissEnisaEventMock: vi.fn(),
  reopenEnisaEventMock: vi.fn(),
  closeEnisaEventMock: vi.fn(),
  submitEnisaMilestoneMock: vi.fn(),
  saveEnisaDraftMock: vi.fn(),
  setEnisaCorrectiveDateMock: vi.fn(),
  exportEnisaMilestoneMock: vi.fn(),
}));

vi.mock('@/api/enisa', () => ({
  getEnisaEvent: getEnisaEventMock,
  confirmEnisaEvent: confirmEnisaEventMock,
  dismissEnisaEvent: dismissEnisaEventMock,
  reopenEnisaEvent: reopenEnisaEventMock,
  closeEnisaEvent: closeEnisaEventMock,
  submitEnisaMilestone: submitEnisaMilestoneMock,
  saveEnisaDraft: saveEnisaDraftMock,
  setEnisaCorrectiveDate: setEnisaCorrectiveDateMock,
  exportEnisaMilestone: exportEnisaMilestoneMock,
}));

function buildDetail(overrides: Partial<EnisaEventDetailData> = {}): EnisaEventDetailData {
  return {
    id: 1,
    tree_id: 1,
    cve_id: 'CVE-2026-0001',
    status: 'candidate',
    detected_at: '2026-07-22T10:00:00Z',
    last_detected_at: '2026-07-22T10:00:00Z',
    confirmed_at: null,
    redetection_count: 0,
    milestones: {},
    corrective_available_at: null,
    affected_assets: [],
    evaluation_context: { decision: 'Act' },
    drafts: {},
    confirmed_by: null,
    dismissed_by: null,
    dismiss_reason: null,
    close_reason: null,
    ...overrides,
  };
}

// Localise l'input d'un champ de brouillon par son libellé (attribut title)
// plutôt que par valeur affichée : plusieurs champs (dont le "Correctif
// disponible le" du cycle de vie) peuvent partager une valeur vide et
// rendraient findByDisplayValue('') ambigu.
function getDraftFieldInput(key: string): HTMLInputElement {
  const label = screen.getByTitle(key);
  return within(label.parentElement as HTMLElement).getByRole('textbox') as HTMLInputElement;
}

describe('EnisaEventDetail — helpers datetime-local <-> ISO', () => {
  it('fait l\'aller-retour datetimeLocalToIso -> isoToDatetimeLocal sur une date locale donnée', () => {
    const local = '2026-07-22T14:30';
    const iso = datetimeLocalToIso(local);
    expect(iso).not.toBeNull();
    // Reconvertir l'ISO obtenu doit redonner exactement la valeur locale de départ
    expect(isoToDatetimeLocal(iso)).toBe(local);
  });

  it('gère les entrées vides/nulles sans lever', () => {
    expect(datetimeLocalToIso('')).toBeNull();
    expect(isoToDatetimeLocal(null)).toBe('');
  });
});

describe('EnisaEventDetail — actions selon le statut', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('candidate affiche Confirmer / Rejeter', async () => {
    getEnisaEventMock.mockResolvedValue(buildDetail({ status: 'candidate' }));
    render(<EnisaEventDetail eventId={1} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('Confirmer')).toBeInTheDocument();
      expect(screen.getByText('Rejeter')).toBeInTheDocument();
    });
  });

  it('dismissed affiche Réouvrir', async () => {
    getEnisaEventMock.mockResolvedValue(
      buildDetail({ status: 'dismissed', dismiss_reason: 'Faux positif' })
    );
    render(<EnisaEventDetail eventId={2} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('Réouvrir')).toBeInTheDocument();
    });
  });

  it('confirmed affiche les actions par jalon et Clôturer', async () => {
    getEnisaEventMock.mockResolvedValue(
      buildDetail({
        status: 'confirmed',
        milestones: {
          early_warning: {
            due_at: '2026-07-23T10:00:00Z',
            remaining_seconds: 86400,
            overdue: false,
            submitted_at: null,
          },
          notification: {
            due_at: '2026-07-27T10:00:00Z',
            remaining_seconds: 400000,
            overdue: false,
            submitted_at: null,
          },
          final_report: {
            due_at: null,
            remaining_seconds: null,
            overdue: false,
            submitted_at: null,
          },
        },
      })
    );
    render(<EnisaEventDetail eventId={3} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getAllByText('Éditer le formulaire').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Marquer comme soumis').length).toBe(3);
      expect(screen.getByText('Clôturer')).toBeInTheDocument();
    });
  });
});

describe('EnisaEventDetail — clôture : motif requis si jalons non soumis', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function confirmedDetailPartiallySubmitted(): EnisaEventDetailData {
    return buildDetail({
      status: 'confirmed',
      milestones: {
        early_warning: {
          due_at: '2026-07-20T10:00:00Z',
          remaining_seconds: 0,
          overdue: false,
          submitted_at: '2026-07-20T09:00:00Z',
        },
        notification: {
          due_at: '2026-07-25T10:00:00Z',
          remaining_seconds: 100000,
          overdue: false,
          submitted_at: null,
        },
        final_report: {
          due_at: null,
          remaining_seconds: null,
          overdue: false,
          submitted_at: null,
        },
      },
    });
  }

  it("sans motif, le bouton de clôture reste désactivé et closeEnisaEvent n'est pas appelé", async () => {
    getEnisaEventMock.mockResolvedValue(confirmedDetailPartiallySubmitted());
    render(<EnisaEventDetail eventId={4} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() => expect(screen.getByText('Clôturer')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Clôturer'));
    const closeButton = await screen.findByText('Confirmer la clôture');
    expect(closeButton).toBeDisabled();

    fireEvent.click(closeButton);
    expect(closeEnisaEventMock).not.toHaveBeenCalled();
  });

  it('avec un motif, la clôture appelle closeEnisaEvent après confirmation', async () => {
    const user = userEvent.setup();
    getEnisaEventMock.mockResolvedValue(confirmedDetailPartiallySubmitted());
    closeEnisaEventMock.mockResolvedValue(
      buildDetail({ status: 'closed', close_reason: 'Correctif indisponible' })
    );
    render(<EnisaEventDetail eventId={4} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() => expect(screen.getByText('Clôturer')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Clôturer'));
    const reasonInput = await screen.findByPlaceholderText(/Motif \(requis/i);
    await user.type(reasonInput, 'Correctif indisponible');

    const closeButton = screen.getByText('Confirmer la clôture');
    expect(closeButton).not.toBeDisabled();
    fireEvent.click(closeButton);

    // La clôture passe par useConfirm : il faut valider la ConfirmDialog
    const confirmButton = await screen.findByText('Confirm');
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(closeEnisaEventMock).toHaveBeenCalledWith(4, 'Correctif indisponible');
    });
  });
});

describe('EnisaEventDetail — formulaire de jalon', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('pré-remplit le formulaire depuis exportEnisaMilestone puis enregistre le brouillon édité', async () => {
    const user = userEvent.setup();
    getEnisaEventMock.mockResolvedValue(
      buildDetail({
        status: 'confirmed',
        milestones: {
          early_warning: {
            due_at: '2026-07-23T10:00:00Z',
            remaining_seconds: 86400,
            overdue: false,
            submitted_at: null,
          },
        },
      })
    );
    exportEnisaMilestoneMock.mockResolvedValue(
      JSON.stringify({ summary: 'Résumé pré-rempli' })
    );
    saveEnisaDraftMock.mockResolvedValue(buildDetail({ status: 'confirmed' }));

    render(<EnisaEventDetail eventId={5} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getAllByText('Éditer le formulaire')[0]).toBeInTheDocument()
    );
    fireEvent.click(screen.getAllByText('Éditer le formulaire')[0]);

    const field = await screen.findByDisplayValue('Résumé pré-rempli');
    await user.clear(field);
    await user.type(field, 'Résumé édité');

    fireEvent.click(screen.getByText('Enregistrer le brouillon'));

    await waitFor(() => {
      expect(saveEnisaDraftMock).toHaveBeenCalledWith(5, 'early_warning', {
        summary: 'Résumé édité',
      });
    });
  });

  it('préserve les champs structurés (jamais stringifiés) et ne renvoie que la clé éditée', async () => {
    const user = userEvent.setup();
    getEnisaEventMock.mockResolvedValue(
      buildDetail({
        status: 'confirmed',
        milestones: {
          notification: {
            due_at: '2026-07-25T10:00:00Z',
            remaining_seconds: 200000,
            overdue: false,
            submitted_at: null,
          },
        },
      })
    );
    exportEnisaMilestoneMock.mockResolvedValue(
      JSON.stringify({
        corrective_measures: '',
        severity: { cvss_score: 9.8, epss_score: 0.7 },
        affected_assets: [{ asset_id: 'srv-prod-001' }],
      })
    );
    saveEnisaDraftMock.mockResolvedValue(buildDetail({ status: 'confirmed' }));

    render(<EnisaEventDetail eventId={6} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getAllByText('Éditer le formulaire')[1]).toBeInTheDocument()
    );
    // Index 1 = jalon "notification" (ordre MILESTONES : early_warning, notification, final_report)
    fireEvent.click(screen.getAllByText('Éditer le formulaire')[1]);

    await waitFor(() => expect(screen.getByTitle('corrective_measures')).toBeInTheDocument());
    const field = getDraftFieldInput('corrective_measures');
    await user.type(field, 'Correctif appliqué le 2026-07-22');

    // Les champs structurés ne doivent jamais apparaître comme des <input>
    // éditables (ce qui les figerait en JSON stringifié au save) : ils sont
    // affichés en lecture seule.
    expect(screen.queryByDisplayValue(/"cvss_score"/)).not.toBeInTheDocument();
    expect(screen.getByText(/"cvss_score": 9.8/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Enregistrer le brouillon'));

    await waitFor(() => {
      expect(saveEnisaDraftMock).toHaveBeenCalledWith(6, 'notification', {
        corrective_measures: 'Correctif appliqué le 2026-07-22',
      });
    });
  });

  it('fusionne avec le brouillon déjà persisté au lieu de l\'écraser lors d\'un save partiel', async () => {
    const user = userEvent.setup();
    getEnisaEventMock.mockResolvedValue(
      buildDetail({
        status: 'confirmed',
        drafts: { notification: { corrective_measures: 'Mesure déjà enregistrée' } },
        milestones: {
          notification: {
            due_at: '2026-07-25T10:00:00Z',
            remaining_seconds: 200000,
            overdue: false,
            submitted_at: null,
          },
        },
      })
    );
    // L'export reflète déjà la fusion prefill + brouillon existant côté backend
    exportEnisaMilestoneMock.mockResolvedValue(
      JSON.stringify({
        corrective_measures: 'Mesure déjà enregistrée',
        exploitation_active: false,
      })
    );
    saveEnisaDraftMock.mockResolvedValue(buildDetail({ status: 'confirmed' }));

    render(<EnisaEventDetail eventId={7} onClose={vi.fn()} onChanged={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getAllByText('Éditer le formulaire')[1]).toBeInTheDocument()
    );
    // Index 1 = jalon "notification" (ordre MILESTONES : early_warning, notification, final_report)
    fireEvent.click(screen.getAllByText('Éditer le formulaire')[1]);

    await waitFor(() => expect(screen.getByTitle('exploitation_active')).toBeInTheDocument());
    const field = getDraftFieldInput('exploitation_active');
    await user.clear(field);
    await user.type(field, 'true');

    fireEvent.click(screen.getByText('Enregistrer le brouillon'));

    await waitFor(() => {
      expect(saveEnisaDraftMock).toHaveBeenCalledWith(7, 'notification', {
        corrective_measures: 'Mesure déjà enregistrée',
        exploitation_active: 'true',
      });
    });
  });
});
