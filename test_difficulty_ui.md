# Difficulty UI Update Test Plan

## Changes Made:
1. **MetadataModal (Upload)**: Replaced difficulty dropdown with color-coded buttons
2. **BeatmapDetails Edit Form**: Added difficulty override section with color-coded buttons

## Color Scheme:
- **Auto-Detect**: Gray (#6b7280)
- **EASY**: Green (#22c55e)
- **MEDIUM**: Yellow (#eab308)
- **HARD**: Orange (#f97316)
- **EXTREME**: Red (#ef4444)

## Test Cases:

### Upload Flow:
1. Upload an audio file
2. In metadata modal, verify:
   - Default selection shows "Auto-Detect" as active (gray)
   - Clicking difficulty buttons changes selection and color
   - Selected button has solid background, others are outlined
   - Save functionality works with button selections

### Edit Flow:
1. Navigate to existing beatmap details
2. Click "Edit" button
3. Verify:
   - Difficulty override section is present with color-coded buttons
   - Current difficulty is properly selected
   - Clicking buttons updates selection state
   - Save preserves the selected difficulty and triggers backend update

### Backend Integration:
1. Verify that difficulty overrides trigger notes.csv regeneration
2. Check that "AUTO" selection uses detected difficulty
3. Confirm explicit difficulty selections override detection

## Visual Verification:
- Both upload and edit UIs should have consistent color-coded button styling
- Hover states should work properly
- Selected buttons should be clearly distinguishable from unselected ones
- Mobile/responsive behavior should be acceptable
