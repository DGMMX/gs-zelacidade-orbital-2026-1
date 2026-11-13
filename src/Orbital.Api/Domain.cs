using Microsoft.EntityFrameworkCore;
namespace Orbital.Api;

public sealed class AreaMonitorada {
    public int Id { get; set; }
    public string Nome { get; set; } = "";
    public string Municipio { get; set; } = "";
    public decimal Latitude { get; set; }
    public decimal Longitude { get; set; }
}
public sealed class Alerta {
    public int Id { get; set; }
    public int AreaMonitoradaId { get; set; }
    public string Titulo { get; set; } = "";
    public string FonteOrbital { get; set; } = "";
    public string ReferenciaObservacao { get; set; } = "";
    public string Status { get; set; } = "aberto";
}
public record AreaInput(string Nome, string Municipio, decimal Latitude, decimal Longitude);
public record AlertaInput(int AreaMonitoradaId, string Titulo, string FonteOrbital, string ReferenciaObservacao, string Status);
public static class Rules {
    public static string? Validate(AreaInput value) =>
        string.IsNullOrWhiteSpace(value.Nome) || string.IsNullOrWhiteSpace(value.Municipio)
        ? "Nome e municipio sao obrigatorios."
        : value.Nome.Length > 120 || value.Municipio.Length > 120 ? "Limite de 120 caracteres."
        : value.Latitude is < -90 or > 90 || value.Longitude is < -180 or > 180 ? "Coordenadas invalidas." : null;
    public static string? Validate(AlertaInput value) =>
        value.AreaMonitoradaId <= 0 || string.IsNullOrWhiteSpace(value.Titulo) || string.IsNullOrWhiteSpace(value.FonteOrbital) || string.IsNullOrWhiteSpace(value.ReferenciaObservacao)
        ? "Area, titulo, fonte orbital e referencia sao obrigatorios."
        : value.Titulo.Length > 150 || value.FonteOrbital.Length > 120 || value.ReferenciaObservacao.Length > 500 ? "Texto muito longo."
        : !new[] { "aberto", "analise", "resolvido" }.Contains(value.Status) ? "Status invalido." : null;
}
public sealed class OrbitalDb(DbContextOptions<OrbitalDb> options) : DbContext(options) {
    public DbSet<AreaMonitorada> Areas => Set<AreaMonitorada>();
    public DbSet<Alerta> Alertas => Set<Alerta>();
    protected override void OnModelCreating(ModelBuilder m) {
        m.Entity<AreaMonitorada>(e => {
            e.ToTable("AreasMonitoradas"); e.HasKey(x => x.Id);
            e.Property(x => x.Nome).HasMaxLength(120).IsRequired();
            e.Property(x => x.Municipio).HasMaxLength(120).IsRequired();
            e.Property(x => x.Latitude).HasPrecision(9, 6);
            e.Property(x => x.Longitude).HasPrecision(9, 6);
        });
        m.Entity<Alerta>(e => {
            e.ToTable("Alertas"); e.HasKey(x => x.Id);
            e.Property(x => x.Titulo).HasMaxLength(150).IsRequired();
            e.Property(x => x.FonteOrbital).HasMaxLength(120).IsRequired();
            e.Property(x => x.ReferenciaObservacao).HasMaxLength(500).IsRequired();
            e.Property(x => x.Status).HasMaxLength(20).IsRequired();
            e.HasOne<AreaMonitorada>().WithMany().HasForeignKey(x => x.AreaMonitoradaId).OnDelete(DeleteBehavior.Restrict);
        });
    }
}
