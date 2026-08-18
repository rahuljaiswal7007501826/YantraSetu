import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'

import './index.css'
import App from './App.jsx'
import { queryClient } from './lib/queryClient'
import { RoleProvider } from './context/RoleContext'
import { DemoProvider } from './context/DemoContext'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RoleProvider>
        <DemoProvider>
          <App />
        </DemoProvider>
      </RoleProvider>
    </QueryClientProvider>
  </StrictMode>,
)
