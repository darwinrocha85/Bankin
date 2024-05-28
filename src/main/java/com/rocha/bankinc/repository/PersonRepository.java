package com.rocha.bankinc.repository;

import java.util.List;

import com.rocha.bankinc.entity.Person;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;


@Repository
public interface PersonRepository extends JpaRepository<Person, Long>{

    List<Person> findByName(@Param("name") String name);
    List<Person> findByProductId(@Param("productId") int productId);

}
