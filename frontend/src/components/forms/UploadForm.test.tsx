import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../test/utils'
import { UploadForm } from './UploadForm'

// Mock platform utilities
vi.mock('../../utils/platform', () => ({
  isNativePlatform: () => false,
  isWeb: () => true,
  isIOS: () => false,
  isAndroid: () => false,
  getPlatform: () => 'web',
}))

// Mock camera service
vi.mock('../../services/cameraService', () => ({
  captureRecipePhoto: vi.fn(),
}))

// Mock recipesApi
vi.mock('../../services/recipesApi', () => ({
  recipesApi: {
    getFeatures: vi.fn().mockResolvedValue({ youtube_import_enabled: false }),
  },
}))

// Mock cookbooksApi
vi.mock('../../services/cookbooksApi', () => ({
  cookbooksApi: {
    searchCookbooks: vi.fn().mockResolvedValue({ cookbooks: [] }),
    searchGoogleBooks: vi.fn().mockResolvedValue({ books: [] }),
    createCookbookFromGoogleBooks: vi.fn(),
  },
}))

describe('UploadForm', () => {
  const mockOnSubmit = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Mode Selection', () => {
    it('renders all upload mode buttons', () => {
      render(<UploadForm onSubmit={mockOnSubmit} />)

      // Use more specific text patterns including the emojis
      expect(screen.getByText(/📷 image/i)).toBeInTheDocument()
      expect(screen.getByText(/📝 text/i)).toBeInTheDocument()
      expect(screen.getByText(/🔗 url/i)).toBeInTheDocument()
      expect(screen.getByText(/🎬 video/i)).toBeInTheDocument()
    })

    it('starts in image mode by default', () => {
      render(<UploadForm onSubmit={mockOnSubmit} />)

      // Should show image upload area
      expect(screen.getByText(/drop your recipe image/i)).toBeInTheDocument()
    })

    it('switches to text mode when text button clicked', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/📝 text/i))

      // Should show text input area
      expect(screen.getByText(/recipe text/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/example:/i)).toBeInTheDocument()
    })

    it('switches to URL mode when URL button clicked', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/🔗 url/i))

      // Should show URL input area
      expect(screen.getByPlaceholderText(/https:\/\/example.com/i)).toBeInTheDocument()
    })

    it('switches to video mode when video button clicked', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/🎬 video/i))

      // Should show video upload area
      expect(screen.getByText(/recipe video/i)).toBeInTheDocument()
    })

    it('respects initialMode prop', () => {
      render(<UploadForm onSubmit={mockOnSubmit} initialMode="url" />)

      // Should start in URL mode
      expect(screen.getByPlaceholderText(/https:\/\/example.com/i)).toBeInTheDocument()
    })
  })

  describe('Text Mode', () => {
    it('allows entering recipe text', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/📝 text/i))

      const textarea = screen.getByPlaceholderText(/example:/i)
      await user.type(textarea, 'My Test Recipe')

      expect(textarea).toHaveValue('My Test Recipe')
    })

    it('shows character count', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/📝 text/i))

      const textarea = screen.getByPlaceholderText(/example:/i)
      await user.type(textarea, 'Test')

      expect(screen.getByText(/4 \/ 50,000 characters/i)).toBeInTheDocument()
    })
  })

  describe('URL Mode', () => {
    it('allows entering a URL', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/🔗 url/i))

      const urlInput = screen.getByPlaceholderText(/https:\/\/example.com/i)
      await user.type(urlInput, 'https://example.com/recipe')

      expect(urlInput).toHaveValue('https://example.com/recipe')
    })

    it('shows privacy notice for URL imports', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/🔗 url/i))

      expect(screen.getByText(/personal use only/i)).toBeInTheDocument()
    })
  })

  describe('Image Upload', () => {
    it('shows drag and drop zone in image mode', () => {
      render(<UploadForm onSubmit={mockOnSubmit} />)

      expect(screen.getByText(/drop your recipe image/i)).toBeInTheDocument()
      expect(screen.getByText(/or click to browse files/i)).toBeInTheDocument()
    })

    it('accepts valid image file types', async () => {
      render(<UploadForm onSubmit={mockOnSubmit} />)

      const dropZone = screen.getByText(/drop your recipe image/i).parentElement?.parentElement

      // Verify the accept attribute on the hidden input
      const fileInput = dropZone?.querySelector('input[type="file"]')
      expect(fileInput).toHaveAttribute(
        'accept',
        'image/png,image/jpg,image/jpeg,image/gif,image/bmp,image/tiff'
      )
    })
  })

  describe('Recipe Source Selection', () => {
    it('shows recipe source options in image mode', () => {
      render(<UploadForm onSubmit={mockOnSubmit} />)

      expect(screen.getByText(/this is my own recipe/i)).toBeInTheDocument()
      expect(screen.getByText(/this is from a cookbook/i)).toBeInTheDocument()
    })

    it('hides recipe source options in URL mode', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/🔗 url/i))

      expect(screen.queryByText(/this is my own recipe/i)).not.toBeInTheDocument()
    })

    it('hides recipe source options in video mode', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/🎬 video/i))

      expect(screen.queryByText(/this is my own recipe/i)).not.toBeInTheDocument()
    })
  })

  describe('Cookbook Options', () => {
    it('shows cookbook options', () => {
      render(<UploadForm onSubmit={mockOnSubmit} />)

      expect(screen.getByText(/no cookbook \(standalone recipe\)/i)).toBeInTheDocument()
      expect(screen.getByText(/search for cookbook/i)).toBeInTheDocument()
      expect(screen.getByText(/create new cookbook/i)).toBeInTheDocument()
    })

    it('shows new cookbook form when "create new cookbook" is selected', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/create new cookbook/i))

      expect(screen.getByPlaceholderText(/enter cookbook title/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/enter author name/i)).toBeInTheDocument()
    })

    it('uses initialCookbookData when provided', () => {
      render(
        <UploadForm
          onSubmit={mockOnSubmit}
          initialCookbookData={{ cookbookId: 123, cookbookTitle: 'Test Cookbook' }}
        />
      )

      // The no cookbook option should not be selected
      const noCookbookRadio = screen.getByLabelText(/no cookbook \(standalone recipe\)/i) as HTMLInputElement
      expect(noCookbookRadio.checked).toBe(false)
    })
  })

  describe('Translation Option', () => {
    it('shows translation checkbox', () => {
      render(<UploadForm onSubmit={mockOnSubmit} />)

      expect(screen.getByText(/translate to english/i)).toBeInTheDocument()
    })

    it('allows toggling translation option', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).not.toBeChecked()

      await user.click(checkbox)
      expect(checkbox).toBeChecked()
    })
  })

  describe('Form Submission', () => {
    it('disables submit button when no content is provided', () => {
      render(<UploadForm onSubmit={mockOnSubmit} />)

      const submitButton = screen.getByRole('button', { name: /upload recipe/i })
      expect(submitButton).toBeDisabled()
    })

    it('disables submit button when URL mode has no URL', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/🔗 url/i))

      const submitButton = screen.getByRole('button', { name: /upload recipe/i })
      expect(submitButton).toBeDisabled()
    })

    it('enables submit button when URL is provided', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/🔗 url/i))

      const urlInput = screen.getByPlaceholderText(/https:\/\/example.com/i)
      await user.type(urlInput, 'https://example.com/recipe')

      const submitButton = screen.getByRole('button', { name: /upload recipe/i })
      expect(submitButton).not.toBeDisabled()
    })

    it('disables submit button when text mode has no text', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/📝 text/i))

      // Select recipe source to enable form validation
      const ownRecipeRadio = screen.getByLabelText(/this is my own recipe/i)
      await user.click(ownRecipeRadio)

      const submitButton = screen.getByRole('button', { name: /upload recipe/i })
      expect(submitButton).toBeDisabled()
    })

    it('submits form with URL data', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/🔗 url/i))

      const urlInput = screen.getByPlaceholderText(/https:\/\/example.com/i)
      await user.type(urlInput, 'https://example.com/recipe')

      const submitButton = screen.getByRole('button', { name: /upload recipe/i })
      await user.click(submitButton)

      expect(mockOnSubmit).toHaveBeenCalledTimes(1)
      const submittedData = mockOnSubmit.mock.calls[0][0]
      expect(submittedData.isUrlMode).toBe(true)
      expect(submittedData.recipeUrl).toBe('https://example.com/recipe')
    })

    it('submits form with text data', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      await user.click(screen.getByText(/📝 text/i))

      const textarea = screen.getByPlaceholderText(/example:/i)
      await user.type(textarea, 'My Test Recipe\n\nIngredients:\n- 1 cup flour')

      // Select recipe source
      const ownRecipeRadio = screen.getByLabelText(/this is my own recipe/i)
      await user.click(ownRecipeRadio)

      const submitButton = screen.getByRole('button', { name: /upload recipe/i })
      await user.click(submitButton)

      expect(mockOnSubmit).toHaveBeenCalledTimes(1)
      const submittedData = mockOnSubmit.mock.calls[0][0]
      expect(submittedData.isTextMode).toBe(true)
      expect(submittedData.recipeText).toContain('My Test Recipe')
    })

    it('shows loading state when isLoading is true', () => {
      render(<UploadForm onSubmit={mockOnSubmit} isLoading={true} />)

      expect(screen.getByText(/converting/i)).toBeInTheDocument()
    })

    it('disables form when isLoading', () => {
      render(<UploadForm onSubmit={mockOnSubmit} isLoading={true} />)

      const submitButton = screen.getByRole('button', { name: /converting/i })
      expect(submitButton).toBeDisabled()
    })
  })

  describe('Error Display', () => {
    it('displays error message when provided', () => {
      render(<UploadForm onSubmit={mockOnSubmit} error="Upload failed" />)

      expect(screen.getByText('Upload failed')).toBeInTheDocument()
    })
  })

  describe('Validation', () => {
    it('shows warning when recipe from cookbook has no cookbook linked', async () => {
      const user = userEvent.setup()
      render(<UploadForm onSubmit={mockOnSubmit} />)

      // Select "from cookbook" option
      const fromCookbookRadio = screen.getByLabelText(/this is from a cookbook/i)
      await user.click(fromCookbookRadio)

      // Warning should appear since no cookbook is linked and "no cookbook" is still selected
      await waitFor(() => {
        expect(screen.getByText(/please select a cookbook option/i)).toBeInTheDocument()
      })
    })
  })
})
