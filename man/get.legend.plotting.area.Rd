% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/plotting.R
\name{get.legend.plotting.area}
\alias{get.legend.plotting.area}
\title{Get the legend plotting area.}
\usage{
get.legend.plotting.area(
  plot.type = c("baseR", "SVG")[1],
  suppress.warnings = FALSE
)
}
\arguments{
\item{plot.type}{Can be either "baseR" or "SVG" and specifies to which type of plotting
the mapping applies.}

\item{suppress.warnings}{\emph{Logical}, if \code{TRUE} don't show any
warnings.}
}
\value{
A numeric vector with components \emph{x.min}, \emph{x.max},
\emph{y.min} and \emph{y.max}, or \code{NULL} in case of error or no
legend being shown.
}
\description{
Returns the legend plotting area rectangle in plotting coordinates
(if any).
}
\details{
This is intended for advanced users only.
}
