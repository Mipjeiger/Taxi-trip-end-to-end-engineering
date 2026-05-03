import React from 'react';
import { Barchart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

interface MetricsProps {
  data: Array<{ data: string; rides: number; revenue: number }>;
}