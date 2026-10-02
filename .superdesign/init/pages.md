# Complete page dependencies

## frontend/app/(workspace)/analysis/page.tsx
- frontend/app/(workspace)/analysis/page.tsx
  - frontend/components/analysis-workspace.tsx
    - frontend/lib/api.ts
    - frontend/lib/utils.ts
    - frontend/types/index.ts
    - frontend/components/ui/button.tsx
    - frontend/components/common.tsx
    - frontend/components/trajectory-chart.tsx
      - frontend/components/trained-prediction.tsx
    - frontend/components/volume-explorer.tsx
      - frontend/components/volume-canvas.tsx
        - frontend/lib/volume-viewer.ts
    - frontend/components/baseline-forecast.tsx
      - frontend/lib/use-resource.ts


## frontend/app/(workspace)/dashboard/page.tsx
- frontend/app/(workspace)/dashboard/page.tsx
  - frontend/components/common.tsx
    - frontend/types/index.ts
  - frontend/components/ui/button.tsx
    - frontend/lib/utils.ts
  - frontend/components/patient-table.tsx
    - frontend/components/trained-prediction.tsx
  - frontend/components/trajectory-chart.tsx
  - frontend/lib/use-resource.ts
    - frontend/lib/api.ts


## frontend/app/(workspace)/patients/page.tsx
- frontend/app/(workspace)/patients/page.tsx
  - frontend/components/ui/button.tsx
    - frontend/lib/utils.ts
  - frontend/components/common.tsx
    - frontend/types/index.ts
  - frontend/components/patient-table.tsx
    - frontend/components/trained-prediction.tsx
  - frontend/lib/use-resource.ts
    - frontend/lib/api.ts


## frontend/app/(workspace)/patients/[id]/page.tsx
- frontend/app/(workspace)/patients/[id]/page.tsx
  - frontend/components/analysis-workspace.tsx
    - frontend/lib/api.ts
    - frontend/lib/utils.ts
    - frontend/types/index.ts
    - frontend/components/ui/button.tsx
    - frontend/components/common.tsx
    - frontend/components/trajectory-chart.tsx
      - frontend/components/trained-prediction.tsx
    - frontend/components/volume-explorer.tsx
      - frontend/components/volume-canvas.tsx
        - frontend/lib/volume-viewer.ts
    - frontend/components/baseline-forecast.tsx
      - frontend/lib/use-resource.ts


## frontend/app/(workspace)/reports/page.tsx
- frontend/app/(workspace)/reports/page.tsx
  - frontend/components/common.tsx
    - frontend/types/index.ts
  - frontend/components/ui/button.tsx
    - frontend/lib/utils.ts
  - frontend/lib/use-resource.ts
    - frontend/lib/api.ts


## frontend/app/(workspace)/settings/page.tsx
- frontend/app/(workspace)/settings/page.tsx
  - frontend/components/common.tsx
    - frontend/types/index.ts
  - frontend/lib/use-resource.ts
    - frontend/lib/api.ts


## frontend/app/login/page.tsx
- frontend/app/login/page.tsx
  - frontend/components/ui/button.tsx
    - frontend/lib/utils.ts
  - frontend/components/common.tsx
    - frontend/types/index.ts
  - frontend/lib/api.ts


## frontend/app/page.tsx
- frontend/app/page.tsx

