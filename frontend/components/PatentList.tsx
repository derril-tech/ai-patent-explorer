'use client'

import { useState } from 'react'
import { PatentCard } from './PatentCard'

interface PatentListProps {
  onPatentSelect: (patentId: string) => void
}

export function PatentList({ onPatentSelect }: PatentListProps) {
  // Mock data for now
  const mockPatents = [
    {
      id: 'patent_1',
      title: 'Machine Learning System for Image Recognition',
      abstract: 'A system and method for recognizing objects in digital images using deep learning algorithms...',
      pub_number: 'US20230012345A1',
      prio_date: '2023-01-15',
      pub_date: '2023-07-20',
      assignees: ['Tech Corp', 'AI Labs'],
      inventors: ['John Smith', 'Jane Doe'],
      cpc_codes: ['G06N3/08', 'G06K9/00'],
    },
    {
      id: 'patent_2',
      title: 'Blockchain-based Data Verification Method',
      abstract: 'A method for verifying data integrity using blockchain technology with cryptographic proofs...',
      pub_number: 'US20230012346A1',
      prio_date: '2023-02-10',
      pub_date: '2023-08-15',
      assignees: ['Blockchain Inc'],
      inventors: ['Alice Johnson', 'Bob Wilson'],
      cpc_codes: ['H04L9/32', 'G06F21/64'],
    },
    {
      id: 'patent_3',
      title: 'Quantum Computing Optimization Algorithm',
      abstract: 'An optimization algorithm designed specifically for quantum computing systems...',
      pub_number: 'US20230012347A1',
      prio_date: '2023-03-05',
      pub_date: '2023-09-10',
      assignees: ['Quantum Tech'],
      inventors: ['Charlie Brown', 'Diana Prince'],
      cpc_codes: ['G06N10/00', 'G06F17/11'],
    }
  ]

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Patent Portfolio</h2>
          <p className="card-description">
            Browse and manage your patent collection
          </p>
        </div>
        <div className="card-content">
          <div className="grid gap-4">
            {mockPatents.map((patent) => (
              <PatentCard
                key={patent.id}
                patent={patent}
                onClick={() => onPatentSelect(patent.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
